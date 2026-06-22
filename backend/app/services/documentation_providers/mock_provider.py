def generate_mock_documentation(context: dict) -> str:
    repository = context["repository"]
    github = context.get("github")
    github_context = context.get("github_context") or {}

    project_name = github.get("full_name") if github else repository["name"]
    description = (
        repository.get("description")
        or (github.get("description") if github else None)
        or "Описание репозитория пока не заполнено."
    )
    language = github.get("language") if github else repository.get("github_language")

    tree_lines = []

    for item in (github_context.get("tree") or [])[:40]:
        tree_lines.append(f"- `{item.get('path')}` ({item.get('type')})")

    if not tree_lines:
        tree_lines.append("- Структура GitHub-репозитория недоступна.")

    github_file_lines = []

    for file in github_context.get("files") or []:
        github_file_lines.append(f"- `{file.get('path')}`")

    if not github_file_lines:
        github_file_lines.append("- Важные GitHub-файлы не были получены.")

    return "\n".join(
        [
            f"# {project_name}",
            "",
            "## Название проекта",
            str(project_name),
            "",
            "## Краткое описание",
            str(description),
            "",
            "## Ссылка на репозиторий",
            repository["repo_url"],
            "",
            "## Основные технологии",
            language or "Основной язык не определён по данным GitHub.",
            "",
            "## Структура проекта",
            *tree_lines,
            "",
            "## Как запустить проект",
            (
                "Точные команды запуска не найдены в доступных данных. "
                "Их нужно уточнить по README, package.json, requirements.txt, "
                "Dockerfile или другой конфигурации проекта."
            ),
            "",
            "## Основные возможности",
            "- Анализ структуры GitHub-репозитория.",
            "- Получение метаданных репозитория через GitHub API.",
            "- Генерация Markdown-документации.",
            "- Сохранение результата в базе данных приложения.",
            "",
            "## Использованные важные файлы",
            *github_file_lines,
            "",
            "## Что можно улучшить в документации",
            "- Добавить более подробную инструкцию запуска.",
            "- Добавить описание архитектуры проекта.",
            "- Добавить описание переменных окружения.",
            "- Добавить примеры использования API или интерфейса.",
            "",
            "> Это mock-документация. Она создаётся локально без обращения к Gemini API.",
        ]
    )
