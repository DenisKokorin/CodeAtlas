import os

from fastapi import HTTPException

from app import models
from app.services.documentation_providers.gemini_provider import (
    generate_gemini_documentation,
)
from app.services.documentation_providers.mock_provider import (
    generate_mock_documentation,
)
from app.services.github_service import (
    fetch_repository_file_text,
    fetch_repository_info,
    fetch_repository_tree,
)


IMPORTANT_GITHUB_FILENAMES = {
    "readme.md",
    "readme.txt",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "vite.config.ts",
    "vite.config.js",
    "requirements.txt",
    "pyproject.toml",
    "dockerfile",
    "docker-compose.yml",
    "main.py",
    "app.py",
    "app.tsx",
    "app.jsx",
    "index.tsx",
    "index.jsx",
    "server.js",
    "server.ts",
}

IMPORTANT_GITHUB_EXTENSIONS = {
    ".md",
    ".txt",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
}

IGNORED_PATH_PARTS = {
    "node_modules",
    ".git",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    ".next",
    "coverage",
}


def get_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def trim_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value

    return value[:max_chars] + "\n\n[Текст обрезан из-за ограничения размера.]"


def build_prompt(context_text: str) -> str:
    return (
        "Сгенерируй Markdown-документацию для проекта по данным GitHub-репозитория.\n"
        "Не выдумывай факты, если данных нет. Если информации мало, честно "
        "напиши, что часть выводов приблизительная.\n"
        "Учитывай метаданные репозитория, структуру файлов и содержимое важных файлов.\n\n"
        "Обязательно включи разделы:\n"
        "- Название проекта;\n"
        "- Краткое описание;\n"
        "- Основные технологии;\n"
        "- Структура проекта;\n"
        "- Как запустить проект;\n"
        "- Основные возможности;\n"
        "- Что можно улучшить в документации.\n\n"
        f"Контекст проекта:\n{context_text}"
    )


def build_repository_context(repository: models.Repository) -> dict:
    return {
        "name": repository.name,
        "repo_url": repository.repo_url,
        "description": repository.description,
        "status": repository.status,
        "github_full_name": repository.github_full_name,
        "github_default_branch": repository.github_default_branch,
        "github_language": repository.github_language,
        "github_updated_at": repository.github_updated_at,
    }


def is_ignored_path(path: str) -> bool:
    path_parts = set(path.lower().split("/"))
    return bool(path_parts.intersection(IGNORED_PATH_PARTS))


def select_github_text_paths(repository_tree: list[dict], limit: int) -> list[str]:
    selected_paths: list[str] = []

    for item in repository_tree:
        path = item.get("path") or ""
        filename = path.rsplit("/", 1)[-1].lower()

        if item.get("type") != "blob" or is_ignored_path(path):
            continue

        if filename in IMPORTANT_GITHUB_FILENAMES:
            selected_paths.append(path)

        if len(selected_paths) >= limit:
            return selected_paths

    for item in repository_tree:
        path = item.get("path") or ""
        extension = os.path.splitext(path)[1].lower()

        if item.get("type") != "blob" or is_ignored_path(path):
            continue

        if path in selected_paths:
            continue

        if extension in IMPORTANT_GITHUB_EXTENSIONS:
            selected_paths.append(path)

        if len(selected_paths) >= limit:
            break

    return selected_paths


async def build_github_context(repo_url: str, github_info: dict | None) -> dict:
    max_tree_items = get_int_env("DOCUMENTATION_MAX_GITHUB_TREE_ITEMS", 120)
    max_github_files = get_int_env("DOCUMENTATION_MAX_GITHUB_FILES", 8)
    max_github_file_chars = get_int_env(
        "DOCUMENTATION_MAX_GITHUB_FILE_CHARS",
        3000,
    )
    branch = (github_info or {}).get("default_branch") or "main"

    github_context = {
        "tree": [],
        "files": [],
        "tree_error": None,
    }

    try:
        repository_tree = await fetch_repository_tree(
            repo_url=repo_url,
            branch=branch,
            max_items=max_tree_items,
        )
        github_context["tree"] = repository_tree
    except HTTPException as exc:
        github_context["tree_error"] = exc.detail
        return github_context
    except Exception:
        github_context["tree_error"] = "GitHub repository tree is unavailable"
        return github_context

    selected_paths = select_github_text_paths(
        repository_tree=github_context["tree"],
        limit=max_github_files,
    )

    for path in selected_paths:
        try:
            file_text = await fetch_repository_file_text(
                repo_url=repo_url,
                branch=branch,
                path=path,
                max_chars=max_github_file_chars,
            )

            if file_text:
                github_context["files"].append(
                    {
                        "path": path,
                        "content": file_text,
                    }
                )
        except Exception:
            github_context["files"].append(
                {
                    "path": path,
                    "content_error": "GitHub file content is unavailable",
                }
            )

    return github_context


def format_context_for_prompt(context: dict) -> str:
    lines = [
        "## Данные из базы приложения",
        str(context["repository"]),
        "",
        "## Метаданные GitHub API",
        str(context.get("github") or context.get("github_error") or "Недоступны"),
        "",
        "## Структура GitHub-репозитория",
    ]

    github_context = context.get("github_context") or {}
    tree = github_context.get("tree") or []

    if tree:
        for item in tree:
            item_type = item.get("type")
            path = item.get("path")
            size = item.get("size")
            lines.append(f"- {item_type}: {path} ({size or 0} байт)")
    else:
        lines.append(str(github_context.get("tree_error") or "Недоступна"))

    lines.extend(["", "## Важные файлы из GitHub"])

    github_files = github_context.get("files") or []

    if github_files:
        for file in github_files:
            lines.append(f"### {file.get('path')}")
            lines.append(file.get("content") or file.get("content_error") or "")
            lines.append("")
    else:
        lines.append("Важные текстовые файлы из GitHub не были получены.")

    return "\n".join(lines)


async def build_documentation_context(repository: models.Repository) -> dict:
    max_input_chars = get_int_env("DOCUMENTATION_MAX_INPUT_CHARS", 12000)

    github_info = None
    github_error = None

    try:
        github_info = await fetch_repository_info(repository.repo_url)
    except HTTPException as exc:
        github_error = exc.detail
    except Exception:
        github_error = "GitHub API data is unavailable"

    github_context = await build_github_context(
        repo_url=repository.repo_url,
        github_info=github_info,
    )

    context = {
        "repository": build_repository_context(repository),
        "github": github_info,
        "github_error": github_error,
        "github_context": github_context,
    }

    context_text = trim_text(format_context_for_prompt(context), max_input_chars)

    return {
        "repository": context["repository"],
        "github": context["github"],
        "github_error": context["github_error"],
        "github_context": context["github_context"],
        "prompt_context": context_text,
        "source_updated_at": (
            context["github"].get("updated_at") if context["github"] else None
        ),
    }


async def generate_repository_documentation(repository: models.Repository) -> dict:
    context = await build_documentation_context(repository)
    provider_mode = os.getenv("DOCUMENTATION_PROVIDER", "auto").lower()
    api_key = os.getenv("GEMINI_API_KEY", "")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    max_output_tokens = get_int_env("DOCUMENTATION_MAX_OUTPUT_TOKENS", 1200)

    if provider_mode not in {"auto", "mock", "gemini"}:
        provider_mode = "auto"

    if provider_mode == "mock":
        return {
            "documentation": generate_mock_documentation(context),
            "provider": "mock",
            "source_updated_at": context["source_updated_at"],
        }

    if provider_mode == "gemini":
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="Gemini API key is not configured.",
            )

        documentation = await generate_gemini_documentation(
            prompt=build_prompt(context["prompt_context"]),
            api_key=api_key,
            model=model,
            max_output_tokens=max_output_tokens,
        )

        return {
            "documentation": documentation,
            "provider": "gemini",
            "source_updated_at": context["source_updated_at"],
        }

    if api_key:
        try:
            documentation = await generate_gemini_documentation(
                prompt=build_prompt(context["prompt_context"]),
                api_key=api_key,
                model=model,
                max_output_tokens=max_output_tokens,
            )

            return {
                "documentation": documentation,
                "provider": "gemini",
                "source_updated_at": context["source_updated_at"],
            }
        except HTTPException:
            return {
                "documentation": generate_mock_documentation(context),
                "provider": "mock_fallback",
                "source_updated_at": context["source_updated_at"],
            }

    return {
        "documentation": generate_mock_documentation(context),
        "provider": "mock",
        "source_updated_at": context["source_updated_at"],
    }
