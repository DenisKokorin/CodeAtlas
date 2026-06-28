from __future__ import annotations

from typing import Any


IGNORED_DIRECTORIES = {
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
    ".github",
    ".vscode",
    ".idea",
}

PROJECT_FILES = {
    "readme.md",
    "readme.txt",
    "readme.rst",
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "main.py",
    "app.py",
    "index.ts",
    "index.js",
    "server.js",
    "server.ts",
    "app.tsx",
    "app.jsx",
    "index.tsx",
    "index.jsx",
    "vite.config.ts",
    "vite.config.js",
    "webpack.config.js",
    "tsconfig.json",
    ".env.example",
    "makefile",
    "cmakelists.txt",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "cargo.toml",
    "gemfile",
    "setup.py",
    "manage.py",
}

SOURCE_DIRECTORY_NAMES = {
    "src",
    "app",
    "lib",
    "core",
    "backend",
    "frontend",
    "server",
    "client",
    "api",
    "controllers",
    "routes",
    "services",
    "models",
    "views",
    "components",
    "modules",
    "utils",
    "helpers",
    "middleware",
    "handlers",
    "resolvers",
    "mutations",
    "queries",
    "schemas",
    "types",
    "interfaces",
    "pages",
    "features",
    "store",
    "state",
}

CONFIG_DIRECTORY_NAMES = {
    "config",
    "configuration",
    "settings",
    "env",
    "environments",
}

TEST_DIRECTORY_NAMES = {
    "tests",
    "test",
    "spec",
    "__tests__",
    "integration",
    "e2e",
}

MAIN_ENTRY_FILENAMES = {
    "main.py",
    "app.py",
    "index.ts",
    "index.js",
    "server.js",
    "server.ts",
    "app.tsx",
    "app.jsx",
    "manage.py",
    "cli.py",
    "run.py",
}


def _filename(path: str) -> str:
    return path.rsplit("/", 1)[-1].lower()


def _directory_name(path: str) -> str:
    parts = path.split("/")
    if len(parts) <= 1:
        return ""
    return parts[0].lower()


def _is_top_level_dir(path: str) -> bool:
    parts = path.split("/")
    if len(parts) == 1:
        return False
    if len(parts) == 2:
        return True
    return False


def _has_ignored_prefix(path: str) -> bool:
    first_part = path.split("/")[0].lower()
    return first_part in IGNORED_DIRECTORIES


def _tree_paths(github_context: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for item in github_context.get("tree") or []:
        path = item.get("path")
        if path:
            paths.append(str(path))
    return paths


def _map_files_to_directories(paths: list[str]) -> dict[str, list[str]]:
    """Group file paths by their top-level source directory."""
    dirs: dict[str, list[str]] = {}

    for path in paths:
        if _has_ignored_prefix(path):
            continue

        parts = path.split("/")
        top_dir = parts[0].lower() if len(parts) > 1 else ""
        if not top_dir:
            continue

        if top_dir not in dirs:
            dirs[top_dir] = []
        dirs[top_dir].append(path)

    return dirs


def _find_main_entry_files(paths: list[str]) -> list[str]:
    return sorted(
        path for path in paths
        if _filename(path) in MAIN_ENTRY_FILENAMES
    )


def _find_config_files(paths: list[str]) -> list[str]:
    config: list[str] = []
    for path in paths:
        fn = _filename(path)
        if fn in {"dockerfile", "docker-compose.yml", "docker-compose.yaml"}:
            config.append(path)
        elif fn in PROJECT_FILES and fn not in MAIN_ENTRY_FILENAMES:
            config.append(path)
    return sorted(config)


def _detect_language_from_files(paths: list[str]) -> str | None:
    extension_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "React JSX",
        ".ts": "TypeScript",
        ".tsx": "React TSX",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".php": "PHP",
        ".cs": "C#",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".c": "C",
        ".cpp": "C++",
        ".h": "C/C++ Header",
    }

    for path in paths:
        for ext, lang in extension_map.items():
            if path.lower().endswith(ext):
                return lang

    return None


def _classify_directory(dir_name: str, files: list[str], all_paths: list[str]) -> dict[str, Any]:
    """Classify a directory and generate a critical part entry for it."""
    dn = dir_name.lower()

    if dn in SOURCE_DIRECTORY_NAMES:
        num_files = len(files)

        if dn in ("src", "app", "core", "lib"):
            subdirs = set()
            for f in files:
                parts = f.split("/")
                if len(parts) > 2:
                    subdirs.add(parts[1].lower())
            subdirs_str = ", ".join(sorted(subdirs)[:5])

            description = (
                f"Основной каталог исходного кода проекта. "
                f"Содержит {num_files} файлов"
            )
            if subdirs_str:
                description += f", включая подкаталоги: {subdirs_str}"
            description += "."

            return {
                "name": f"Исходный код ({dn}/)",
                "description": description,
                "why_critical": (
                    "Содержит основную логику приложения. "
                    "Изменения в этом каталоге напрямую влияют на функциональность проекта."
                ),
            }

        elif dn == "routes":
            return {
                "name": "API маршруты",
                "description": (
                    f"Определяет HTTP endpoints приложения. "
                    f"Содержит {num_files} файлов с обработчиками запросов."
                ),
                "why_critical": (
                    "Является точкой входа для всех внешних запросов. "
                    "Ошибки здесь приводят к недоступности API."
                ),
            }

        elif dn == "services":
            return {
                "name": "Бизнес-логика",
                "description": (
                    f"Реализует основную бизнес-логику приложения. "
                    f"Содержит {num_files} файлов сервисного слоя."
                ),
                "why_critical": (
                    "Содержит ключевую логику обработки данных. "
                    "Ошибки здесь приводят к некорректной работе системы."
                ),
            }

        elif dn == "models":
            return {
                "name": "Модели данных",
                "description": (
                    f"Определяет структуру данных и ORM-модели. "
                    f"Содержит {num_files} файлов описания сущностей."
                ),
                "why_critical": (
                    "Фундамент для хранения и валидации всех данных приложения."
                ),
            }

        elif dn in ("components", "views", "pages"):
            return {
                "name": "Пользовательский интерфейс",
                "description": (
                    f"UI-компоненты приложения. "
                    f"Содержит {num_files} файлов интерфейса."
                ),
                "why_critical": (
                    "Формирует пользовательский опыт и визуальное представление. "
                    "Критично для удобства использования."
                ),
            }

        elif dn == "middleware":
            return {
                "name": "Middleware и обработка запросов",
                "description": (
                    f"Промежуточные обработчики запросов, "
                    f"отвечающие за аутентификацию, логирование и валидацию. "
                    f"Содержит {num_files} файлов."
                ),
                "why_critical": (
                    "Обрабатывает каждый запрос к системе. Ошибки здесь "
                    "могут заблокировать весь API."
                ),
            }

        elif dn in ("utils", "helpers"):
            return {
                "name": "Вспомогательные модули",
                "description": (
                    f"Содержит утилиты и вспомогательные функции. "
                    f"{num_files} файлов."
                ),
                "why_critical": (
                    "Обеспечивает переиспользуемые компоненты, "
                    "от которых зависят другие модули."
                ),
            }

        elif dn in ("api", "controllers"):
            return {
                "name": "API слой",
                "description": (
                    f"Контроллеры и обработчики API запросов. "
                    f"Содержит {num_files} файлов."
                ),
                "why_critical": (
                    "Обеспечивает интерфейс взаимодействия с внешними системами."
                ),
            }

    if dn in CONFIG_DIRECTORY_NAMES:
        return {
            "name": "Конфигурация проекта",
            "description": (
                f"Файлы конфигурации и настроек проекта. "
                f"Содержит {len(files)} файлов."
            ),
            "why_critical": (
                "Неправильная конфигурация может привести к "
                "некорректной работе всего приложения."
            ),
        }

    if dn in TEST_DIRECTORY_NAMES:
        return {
            "name": "Тесты",
            "description": (
                f"Тестовые файлы проекта. "
                f"Содержит {len(files)} тестов."
            ),
            "why_critical": (
                "Обеспечивает качество и стабильность кода. "
                "Без тестов невозможно гарантировать корректность изменений."
            ),
        }

    # Generic fallback for directories with significant content
    if len(files) >= 3:
        return {
            "name": f"Модуль {dn}",
            "description": (
                f"Каталог {dn}/ содержит {len(files)} файлов "
                f"с реализацией функциональности проекта."
            ),
            "why_critical": (
                "Является значимой частью проекта. "
                "Изменения в этом модуле затрагивают соответствующую функциональность."
            ),
        }

    return None  # Skip small / unknown directories


def build_mock_critical_parts(context: dict) -> dict[str, Any]:
    """Build mock critical parts for any repository based on its actual structure."""
    repository = context["repository"]
    github_context = context.get("github_context") or {}
    paths = _tree_paths(github_context)
    all_paths = [p for p in paths if not _has_ignored_prefix(p)]

    items: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    # 1. Main entry point
    entry_files = _find_main_entry_files(all_paths)
    if entry_files:
        items.append({
            "name": "Точка входа в приложение",
            "description": (
                f"Главный исполняемый файл проекта. "
                f"Отвечает за инициализацию и запуск приложения."
            ),
            "files": entry_files,
            "why_critical": (
                "С этого файла начинается выполнение программы. "
                "Ошибки здесь приводят к невозможности запуска проекта."
            ),
        })
        seen_names.add("Точка входа в приложение")

    # 2. Configuration and project setup
    config_files = _find_config_files(all_paths)
    all_config_files = config_files + [
        p for p in all_paths
        if _filename(p) in PROJECT_FILES and _filename(p) not in MAIN_ENTRY_FILENAMES
        and p not in config_files
    ]
    if all_config_files:
        all_config_files = sorted(set(all_config_files))
        project_setup_files = [f for f in all_config_files if _filename(f) in PROJECT_FILES]

        if project_setup_files:
            language = _detect_language_from_files(all_paths)
            lang_hint = f" ({language})" if language else ""

            items.append({
                "name": f"Конфигурация и сборка{lang_hint}",
                "description": (
                    f"Файлы конфигурации проекта, описывающие зависимости, "
                    f"настройки сборки и параметры окружения."
                ),
                "files": sorted(set(project_setup_files)),
                "why_critical": (
                    "Определяет зависимости, версии и параметры запуска проекта. "
                    "Некорректная конфигурация приводит к ошибкам сборки и выполнения."
                ),
            })
            seen_names.add(f"Конфигурация и сборка{lang_hint}")

    # 3. Classify directories as critical parts
    dir_files = _map_files_to_directories(all_paths)

    # Process source directories first
    for dir_name in sorted(dir_files.keys()):
        if dir_name in SOURCE_DIRECTORY_NAMES:
            entry = _classify_directory(dir_name, dir_files[dir_name], all_paths)
            if entry and entry["name"] not in seen_names:
                entry["files"] = dir_files[dir_name]
                items.append(entry)
                seen_names.add(entry["name"])

    # Then other directories
    for dir_name in sorted(dir_files.keys()):
        if dir_name not in SOURCE_DIRECTORY_NAMES:
            entry = _classify_directory(dir_name, dir_files[dir_name], all_paths)
            if entry and entry["name"] not in seen_names:
                entry["files"] = dir_files[dir_name]
                items.append(entry)
                seen_names.add(entry["name"])

    # 4. Detect and add documentation / readme if present
    readme_files = sorted(
        p for p in all_paths
        if _filename(p) in {"readme.md", "readme.txt", "readme.rst"}
    )
    if readme_files:
        items.append({
            "name": "Документация проекта",
            "description": (
                "README и файлы документации, описывающие "
                "назначение, установку и использование проекта."
            ),
            "files": readme_files,
            "why_critical": (
                "Является первичным источником информации о проекте "
                "для новых разработчиков и пользователей."
            ),
        })

    # 5. CI/CD if present
    ci_cd_files = sorted(
        p for p in all_paths
        if p.lower().startswith(".github/workflows/")
        or _filename(p) in {".gitlab-ci.yml", "azure-pipelines.yml", "jenkinsfile"}
    )
    if ci_cd_files:
        items.append({
            "name": "CI/CD и автоматизация",
            "description": (
                "Конфигурация непрерывной интеграции и доставки. "
                "Автоматизирует сборку, тестирование и развёртывание."
            ),
            "files": ci_cd_files,
            "why_critical": (
                "Обеспечивает автоматическую проверку качества кода "
                "и доставку изменений в продакшн."
            ),
        })

    # 6. Docker if present
    docker_files = sorted(
        p for p in all_paths
        if _filename(p).startswith("docker")
        or _filename(p) in {"docker-compose.yml", "docker-compose.yaml"}
    )
    if docker_files:
        items.append({
            "name": "Контейнеризация (Docker)",
            "description": (
                "Dockerfile и docker-compose конфигурация "
                "для контейнеризации приложения."
            ),
            "files": docker_files,
            "why_critical": (
                "Обеспечивает воспроизводимость окружения. "
                "Без корректной Docker-конфигурации невозможен запуск в контейнере."
            ),
        })

    # 7. Add a general catch-all for important root files
    root_blobs = sorted(
        p for p in all_paths
        if "/" not in p and _filename(p) not in {f.lower() for f in MAIN_ENTRY_FILENAMES}
        and _filename(p) not in PROJECT_FILES
    )
    if root_blobs:
        items.append({
            "name": "Корневые файлы проекта",
            "description": (
                "Файлы в корне проекта, определяющие его структуру "
                "и настройки на верхнем уровне."
            ),
            "files": root_blobs,
            "why_critical": (
                "Формируют общую структуру и конфигурацию проекта. "
                "Ошибки здесь затрагивают весь проект."
            ),
        })

    # 8. Fallback when no tree data is available (GitHub API unavailable)
    if not items:
        language = repository.get("github_language") or "не определён"
        description = repository.get("description") or "Описание не указано"

        items.append({
            "name": "Исходный код",
            "description": (
                f"Основной код проекта на {language}. "
                f"Структура репозитория временно недоступна для детального анализа."
            ),
            "files": [],
            "why_critical": (
                "Содержит всю бизнес-логику и функциональность проекта. "
                "Любые изменения здесь напрямую влияют на работу системы."
            ),
        })

        items.append({
            "name": "API и интеграции",
            "description": (
                "Определяет интерфейсы взаимодействия между компонентами системы "
                "и внешними сервисами."
            ),
            "files": [],
            "why_critical": (
                "Ошибки на этом уровне приводят к нарушению "
                "взаимодействия с внешними системами и пользователями."
            ),
        })

        items.append({
            "name": "База данных и хранение данных",
            "description": (
                "Модели данных и механизмы хранения, "
                "обеспечивающие целостность и доступность информации."
            ),
            "files": [],
            "why_critical": (
                "Потеря или повреждение данных критичны для любого приложения. "
                "Надёжность хранения — основа стабильной работы."
            ),
        })

    return {
        "title": "Critical Parts",
        "items": items,
    }
