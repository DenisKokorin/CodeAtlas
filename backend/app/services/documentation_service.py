import json
import os
import re
from typing import Any

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
from app.services.project_critical_parts_service import (
    build_critical_parts_facts,
    build_mock_critical_parts,
)
from app.services.project_quality_service import (
    build_default_quality_assessment,
    build_project_quality_facts,
    normalize_quality_assessment,
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


def build_prompt(
    context_text: str,
    quality_facts: dict[str, Any],
    critical_parts_facts: dict[str, Any] | None = None,
) -> str:
    quality_facts_json = json.dumps(quality_facts, ensure_ascii=False, indent=2)
    critical_parts_facts_json = json.dumps(
        critical_parts_facts or {},
        ensure_ascii=False,
        indent=2,
    )

    return (
        "Сгенерируй результат анализа GitHub-репозитория.\n"
        "Ответ должен быть СТРОГО валидным JSON без markdown code fence, "
        "без пояснений до JSON и после JSON. Не оборачивай ответ в ```json.\n"
        "Не выдумывай факты, если данных нет. Если информации мало, честно "
        "напиши, что часть выводов приблизительная.\n\n"
        "JSON должен иметь ровно такие верхнеуровневые поля:\n"
        "{\n"
        '  "documentation_markdown_lines": ["# Название проекта", "", "## Краткое описание", "..."],\n'
        '  "business_summary": {\n'
        '    "title": "Business Summary",\n'
        '    "text": "Краткое описание системы для руководителя",\n'
        '    "target_audience": ["..."],\n'
        '    "business_value": ["..."]\n'
        "  },\n"
        '  "quality_assessment": {\n'
        '    "summary": "Человекочитаемая общая оценка проекта",\n'
        '    "strengths": ["..."],\n'
        '    "risks": ["..."],\n'
        '    "recommendations": ["..."]\n'
        "  },\n"
        '  "critical_parts": {\n'
        '    "title": "Critical Parts",\n'
        '    "items": [\n'
        "      {\n"
        '        "name": "Название критической части",\n'
        '        "description": "Описание, почему эта часть важна",\n'
        '        "files": ["путь/к/файлу.py", "путь/к/другому/файлу.js"],\n'
        '        "why_critical": "Почему эта часть является критической для проекта"\n'
        "      }\n"
        "    ]\n"
        "  }\n"
        "}\n\n"
        "Требования к documentation_markdown_lines:\n"
        "- это массив строк, из которого backend соберёт Markdown через перенос строки;\n"
        "- НЕ возвращай документацию одним большим многострочным значением documentation_markdown;\n"
        "- каждая строка Markdown должна быть отдельным элементом массива;\n"
        "- это должна быть обычная техническая Markdown-документация;\n"
        "- не включай туда Business Summary;\n"
        "- не включай туда Project Quality Assessment;\n"
        "- не включай туда Critical Parts;\n"
        "- обязательно включи разделы: Название проекта, Краткое описание, "
        "Основные технологии, Структура проекта, Как запустить проект, "
        "Основные возможности, Что можно улучшить в документации;\n"
        "- пиши достаточно подробно, но компактно, чтобы весь JSON полностью поместился в ответ.\n\n"
        "Требования к business_summary:\n"
        "- пиши простым языком для руководителя или заказчика;\n"
        "- объясни, что делает система, кому она полезна и какую ценность даёт;\n"
        "- не перегружай текст техническими деталями.\n\n"
        "Требования к quality_assessment:\n"
        "- основывайся на переданных фактах о репозитории;\n"
        "- не меняй score и criteria: их считает backend отдельно;\n"
        "- дай понятное summary, strengths, risks и recommendations.\n\n"
        "Требования к critical_parts:\n"
        "- это обязательное поле, ты ОБЯЗАН вернуть critical_parts с непустым items;\n"
        "- используй переданные факты о структуре репозитория, НЕ выдумывай файлы;\n"
        "- для каждой критической части укажи только реальные файлы из фактов ниже;\n"
        "- объясни, почему эта часть критична для работы всего проекта;\n"
        "- выдели от 3 до 6 наиболее важных частей.\n\n"
        "ВАЖНО: Твой JSON-ответ должен содержать ВСЕ четыре верхнеуровневых поля:\n"
        "1. documentation_markdown_lines\n"
        "2. business_summary\n"
        "3. quality_assessment\n"
        "4. critical_parts (обязательно с непустым items)\n"
        "Не пропускай ни одно из них.\n\n"
        "Факты для оценки проекта, собранные backend-ом:\n"
        f"{quality_facts_json}\n\n"
        "Факты о структуре репозитория для critical_parts:\n"
        f"{critical_parts_facts_json}\n\n"
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

    quality_facts = build_project_quality_facts(github_context)
    critical_parts_facts = build_critical_parts_facts(github_context)
    context_text = trim_text(format_context_for_prompt(context), max_input_chars)

    return {
        "repository": context["repository"],
        "github": context["github"],
        "github_error": context["github_error"],
        "github_context": context["github_context"],
        "quality_facts": quality_facts,
        "critical_parts_facts": critical_parts_facts,
        "prompt_context": context_text,
        "source_updated_at": (
            context["github"].get("updated_at") if context["github"] else None
        ),
    }


def build_mock_business_summary(context: dict) -> dict[str, Any]:
    repository = context["repository"]
    github = context.get("github")
    project_name = github.get("full_name") if github else repository["name"]
    description = (
        repository.get("description")
        or (github.get("description") if github else None)
        or "Описание репозитория пока не заполнено."
    )

    return {
        "title": "Business Summary",
        "text": (
            f"{project_name} — проект, который был проанализирован CodeAtlas. "
            f"Система помогает быстро получить техническую документацию, "
            f"краткое описание для руководителя и общую оценку состояния репозитория. "
            f"Краткое описание проекта: {description}"
        ),
        "target_audience": [
            "руководители проектов",
            "разработчики",
            "новые участники команды",
        ],
        "business_value": [
            "ускоряет знакомство с проектом",
            "снижает время на ручное описание репозитория",
            "помогает быстрее оценить состояние проекта",
        ],
    }


def build_mock_structured_result(context: dict) -> dict[str, Any]:
    quality_facts = context["quality_facts"]

    return {
        "documentation_markdown": generate_mock_documentation(context),
        "business_summary": build_mock_business_summary(context),
        "quality_assessment": build_default_quality_assessment(quality_facts),
        "critical_parts": build_mock_critical_parts(context),
    }


def get_github_context_error(context: dict) -> str | None:
    if context.get("github_error"):
        return str(context["github_error"])

    github_context = context.get("github_context") or {}

    if github_context.get("tree_error"):
        return str(github_context["tree_error"])

    if not github_context.get("tree"):
        return "GitHub repository tree is empty or unavailable"

    return None


def ensure_github_context_available_for_gemini(context: dict) -> None:
    github_error = get_github_context_error(context)

    if github_error is None:
        return

    raise HTTPException(
        status_code=502,
        detail=(
            "GitHub repository data is unavailable. Documentation generation "
            "was stopped before calling Gemini. Reason: "
            f"{github_error}. Check repository URL, add GITHUB_API_TOKEN to "
            "backend/.env, or try again later."
        ),
    )


def is_structured_response_error(exc: HTTPException) -> bool:
    detail = str(exc.detail)
    return (
        "structured documentation response" in detail.lower()
        or "documentation_markdown" in detail
        or "business_summary" in detail
    )


def strip_json_code_fence(raw_text: str) -> str:
    text = raw_text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    first_brace = text.find("{")
    last_brace = text.rfind("}")

    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1]

    return text


def repair_common_json_text_issues(json_text: str) -> str:
    """Repair common LLM JSON issues inside string values.

    Gemini can still return almost-valid JSON where Markdown lines contain
    raw control characters or Windows paths like .\\venv\\Scripts\\activate.
    Those backslashes are invalid in strict JSON if they are not escaped.
    This function keeps JSON structure unchanged and only sanitizes characters
    while the scanner is inside a JSON string.
    """

    result: list[str] = []
    in_string = False
    i = 0
    valid_escape_chars = {'"', "\\", "/", "b", "f", "n", "r", "t", "u"}

    while i < len(json_text):
        char = json_text[i]

        if not in_string:
            result.append(char)
            if char == '"':
                in_string = True
            i += 1
            continue

        if char == '"':
            result.append(char)
            in_string = False
            i += 1
            continue

        if char == "\\":
            next_char = json_text[i + 1] if i + 1 < len(json_text) else ""
            if next_char in valid_escape_chars:
                result.append(char)
                if next_char:
                    result.append(next_char)
                    i += 2
                else:
                    i += 1
            else:
                result.append("\\\\")
                i += 1
            continue

        if char == "\n":
            result.append("\\n")
        elif char == "\r":
            result.append("\\r")
        elif char == "\t":
            result.append("\\t")
        else:
            result.append(char)

        i += 1

    return "".join(result)


def load_structured_json(raw_text: str) -> dict[str, Any]:
    json_text = strip_json_code_fence(raw_text)

    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError:
        repaired_json_text = repair_common_json_text_issues(json_text)
        try:
            payload = json.loads(repaired_json_text)
        except json.JSONDecodeError as exc:
            print(
                "Failed to parse structured documentation response. "
                f"Gemini raw response preview: {raw_text[:1200]}"
            )
            print(
                "Failed to parse structured documentation response. "
                f"Repaired response preview: {repaired_json_text[:1200]}"
            )
            raise HTTPException(
                status_code=502,
                detail="Failed to parse structured documentation response. Try again.",
            ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=502,
            detail="Structured documentation response must be a JSON object. Try again.",
        )

    return payload


def parse_structured_documentation_response(
    raw_text: str,
    quality_facts: dict[str, Any],
) -> dict[str, Any]:
    payload = load_structured_json(raw_text)

    documentation_lines = payload.get("documentation_markdown_lines")
    documentation = payload.get("documentation_markdown")

    if isinstance(documentation_lines, list):
        documentation = "\n".join(
            str(line) for line in documentation_lines
        )

    if not isinstance(documentation, str) or not documentation.strip():
        raise HTTPException(
            status_code=502,
            detail=(
                "Structured documentation response does not contain "
                "documentation_markdown_lines. Try again."
            ),
        )

    business_summary = payload.get("business_summary")
    if not isinstance(business_summary, dict):
        raise HTTPException(
            status_code=502,
            detail="Structured documentation response does not contain business_summary. Try again.",
        )

    quality_assessment = normalize_quality_assessment(
        llm_assessment=payload.get("quality_assessment"),
        quality_facts=quality_facts,
    )

    critical_parts = payload.get("critical_parts")
    if not isinstance(critical_parts, dict) or "items" not in critical_parts:
        raise HTTPException(
            status_code=502,
            detail=(
                "Structured documentation response does not contain "
                "critical_parts with items. Try again."
            ),
        )

    return {
        "documentation_markdown": documentation.strip(),
        "business_summary": business_summary,
        "quality_assessment": quality_assessment,
        "critical_parts": critical_parts,
    }


async def generate_repository_documentation(repository: models.Repository) -> dict:
    context = await build_documentation_context(repository)
    provider_mode = os.getenv("DOCUMENTATION_PROVIDER", "auto").lower()
    api_key = os.getenv("GEMINI_API_KEY", "")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    max_output_tokens = get_int_env("DOCUMENTATION_MAX_OUTPUT_TOKENS", 8192)

    if provider_mode not in {"auto", "mock", "gemini"}:
        provider_mode = "auto"

    if provider_mode == "mock":
        structured_result = build_mock_structured_result(context)
        return {
            "documentation": structured_result["documentation_markdown"],
            "business_summary": structured_result["business_summary"],
            "quality_assessment": structured_result["quality_assessment"],
            "critical_parts": structured_result["critical_parts"],
            "provider": "mock",
            "source_updated_at": context["source_updated_at"],
        }

    if provider_mode == "gemini":
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="Gemini API key is not configured.",
            )

        ensure_github_context_available_for_gemini(context)

        raw_documentation = await generate_gemini_documentation(
            prompt=build_prompt(
                context["prompt_context"],
                context["quality_facts"],
                critical_parts_facts=context.get("critical_parts_facts"),
            ),
            api_key=api_key,
            model=model,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
        )

        structured_result = parse_structured_documentation_response(
            raw_text=raw_documentation,
            quality_facts=context["quality_facts"],
        )

        return {
            "documentation": structured_result["documentation_markdown"],
            "business_summary": structured_result["business_summary"],
            "quality_assessment": structured_result["quality_assessment"],
            "critical_parts": structured_result["critical_parts"],
            "provider": "gemini",
            "source_updated_at": context["source_updated_at"],
        }

    if api_key:
        ensure_github_context_available_for_gemini(context)

        try:
            raw_documentation = await generate_gemini_documentation(
                prompt=build_prompt(
                context["prompt_context"],
                context["quality_facts"],
                critical_parts_facts=context.get("critical_parts_facts"),
            ),
                api_key=api_key,
                model=model,
                max_output_tokens=max_output_tokens,
                response_mime_type="application/json",
            )

            structured_result = parse_structured_documentation_response(
                raw_text=raw_documentation,
                quality_facts=context["quality_facts"],
            )

            return {
                "documentation": structured_result["documentation_markdown"],
                "business_summary": structured_result["business_summary"],
                "quality_assessment": structured_result["quality_assessment"],
                "critical_parts": structured_result["critical_parts"],
                "provider": "gemini",
                "source_updated_at": context["source_updated_at"],
            }
        except HTTPException as exc:
            if is_structured_response_error(exc):
                raise

            structured_result = build_mock_structured_result(context)
            return {
                "documentation": structured_result["documentation_markdown"],
                "business_summary": structured_result["business_summary"],
                "quality_assessment": structured_result["quality_assessment"],
                "critical_parts": structured_result["critical_parts"],
                "provider": "mock_fallback",
                "source_updated_at": context["source_updated_at"],
            }

    structured_result = build_mock_structured_result(context)
    return {
        "documentation": structured_result["documentation_markdown"],
        "business_summary": structured_result["business_summary"],
        "quality_assessment": structured_result["quality_assessment"],
        "critical_parts": structured_result["critical_parts"],
        "provider": "mock",
        "source_updated_at": context["source_updated_at"],
    }

async def generate_gemini_raw_debug_response(repository: models.Repository) -> dict[str, Any]:
    """Return raw Gemini response for temporary debugging.

    This function intentionally does not save anything to the database.
    It uses the same GitHub context, quality facts, prompt and Gemini settings
    as normal documentation generation, then returns the raw model output so
    invalid JSON issues can be inspected from Swagger.
    """

    context = await build_documentation_context(repository)
    api_key = os.getenv("GEMINI_API_KEY", "")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    max_output_tokens = get_int_env("DOCUMENTATION_MAX_OUTPUT_TOKENS", 15000)

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="Gemini API key is not configured.",
        )

    ensure_github_context_available_for_gemini(context)

    prompt = build_prompt(
        context["prompt_context"],
        context["quality_facts"],
        critical_parts_facts=context.get("critical_parts_facts"),
    )
    raw_response = await generate_gemini_documentation(
        prompt=prompt,
        api_key=api_key,
        model=model,
        max_output_tokens=max_output_tokens,
        response_mime_type="application/json",
    )

    strict_json_valid = False
    repaired_json_valid = False
    structured_response_valid = False
    parse_error = None

    json_text = strip_json_code_fence(raw_response)

    try:
        json.loads(json_text)
        strict_json_valid = True
        repaired_json_valid = True
    except json.JSONDecodeError as strict_exc:
        parse_error = str(strict_exc)
        repaired_json_text = repair_common_json_text_issues(json_text)

        try:
            json.loads(repaired_json_text)
            repaired_json_valid = True
        except json.JSONDecodeError as repaired_exc:
            parse_error = str(repaired_exc)

    try:
        parse_structured_documentation_response(
            raw_text=raw_response,
            quality_facts=context["quality_facts"],
        )
        structured_response_valid = True
        parse_error = None
    except HTTPException as exc:
        parse_error = str(exc.detail)

    github_context = context.get("github_context") or {}
    files = github_context.get("files") or []

    return {
        "repository_id": repository.id,
        "repository_name": repository.name,
        "repo_url": repository.repo_url,
        "provider": "gemini",
        "model": model,
        "max_output_tokens": max_output_tokens,
        "raw_response_length": len(raw_response),
        "strict_json_valid": strict_json_valid,
        "repaired_json_valid": repaired_json_valid,
        "structured_response_valid": structured_response_valid,
        "parse_error": parse_error,
        "github": context.get("github"),
        "github_error": context.get("github_error"),
        "github_tree_items_count": len(github_context.get("tree") or []),
        "github_files_used": [file.get("path") for file in files],
        "quality_facts": context["quality_facts"],
        "raw_response": raw_response,
    }

