from __future__ import annotations

from typing import Any


QUALITY_CRITERIA = {
    "has_readme": {
        "label_true": "README найден",
        "label_false": "README не найден",
        "description_true": "В репозитории есть README-файл с базовой информацией о проекте.",
        "description_false": "README-файл не найден или не попал в доступную структуру репозитория.",
        "weight": 1.5,
    },
    "has_tests": {
        "label_true": "Тесты найдены",
        "label_false": "Тесты не найдены",
        "description_true": "В репозитории обнаружены тестовые файлы или директории с тестами.",
        "description_false": "В доступной структуре репозитория не обнаружены тестовые файлы.",
        "weight": 2.0,
    },
    "has_ci_cd": {
        "label_true": "CI/CD найден",
        "label_false": "CI/CD не найден",
        "description_true": "В репозитории обнаружены workflow-файлы или конфигурация CI/CD.",
        "description_false": "В доступной структуре репозитория не обнаружены workflow-файлы CI/CD.",
        "weight": 1.5,
    },
    "has_docker": {
        "label_true": "Docker найден",
        "label_false": "Docker не найден",
        "description_true": "В репозитории есть Dockerfile или docker-compose.yml.",
        "description_false": "Dockerfile и docker-compose.yml не найдены в доступной структуре репозитория.",
        "weight": 1.5,
    },
    "has_env_example": {
        "label_true": "Пример переменных окружения найден",
        "label_false": "Пример переменных окружения не найден",
        "description_true": "В репозитории есть .env.example или похожий файл с примером переменных окружения.",
        "description_false": "Файл .env.example или похожий пример переменных окружения не найден.",
        "weight": 1.0,
    },
    "has_dependency_manifest": {
        "label_true": "Файлы зависимостей найдены",
        "label_false": "Файлы зависимостей не найдены",
        "description_true": "В репозитории есть requirements.txt, pyproject.toml, package.json или другой manifest зависимостей.",
        "description_false": "Файлы зависимостей не найдены в доступной структуре репозитория.",
        "weight": 1.0,
    },
    "has_clear_structure": {
        "label_true": "Структура проекта понятна",
        "label_false": "Структура проекта требует уточнения",
        "description_true": "В репозитории видны логические директории или модули приложения.",
        "description_false": "По доступной структуре сложно уверенно определить архитектуру проекта.",
        "weight": 1.5,
    },
}


def _tree_paths(github_context: dict[str, Any]) -> list[str]:
    paths: list[str] = []

    for item in github_context.get("tree") or []:
        path = item.get("path")
        if path:
            paths.append(str(path))

    return paths


def _filename(path: str) -> str:
    return path.rsplit("/", 1)[-1].lower()


def _contains_path_part(path: str, part: str) -> bool:
    return part in {piece.lower() for piece in path.split("/")}


def _matched(paths: list[str], predicate) -> list[str]:
    return sorted(path for path in paths if predicate(path))


def _score_label(score: float) -> str:
    if score >= 8:
        return "Хорошее состояние проекта"
    if score >= 6:
        return "Среднее состояние проекта"
    if score >= 4:
        return "Проект требует доработки"
    return "Проект требует существенных улучшений"


def build_project_quality_facts(github_context: dict[str, Any]) -> dict[str, Any]:
    paths = _tree_paths(github_context)
    lower_paths = [path.lower() for path in paths]

    readme_files = _matched(
        paths,
        lambda path: _filename(path) in {"readme.md", "readme.txt", "readme.rst"},
    )
    test_files = _matched(
        paths,
        lambda path: (
            _contains_path_part(path, "tests")
            or _contains_path_part(path, "test")
            or _filename(path).startswith("test_")
            or _filename(path).endswith("_test.py")
            or ".test." in _filename(path)
            or ".spec." in _filename(path)
        ),
    )
    ci_cd_files = _matched(
        paths,
        lambda path: (
            path.lower().startswith(".github/workflows/")
            or _filename(path) in {".gitlab-ci.yml", "azure-pipelines.yml", "jenkinsfile"}
        ),
    )
    docker_files = _matched(
        paths,
        lambda path: _filename(path) in {"dockerfile", "docker-compose.yml", "docker-compose.yaml"},
    )
    env_example_files = _matched(
        paths,
        lambda path: _filename(path) in {".env.example", "env.example", ".env.sample", "env.sample"},
    )
    dependency_files = _matched(
        paths,
        lambda path: _filename(path)
        in {
            "requirements.txt",
            "pyproject.toml",
            "poetry.lock",
            "package.json",
            "package-lock.json",
            "pnpm-lock.yaml",
            "yarn.lock",
            "pom.xml",
            "build.gradle",
            "go.mod",
        },
    )

    structure_markers = {
        "app",
        "src",
        "backend",
        "frontend",
        "routes",
        "services",
        "models",
        "schemas",
        "controllers",
        "components",
    }
    found_structure_markers = sorted(
        {
            piece.lower()
            for path in lower_paths
            for piece in path.split("/")
            if piece.lower() in structure_markers
        }
    )

    raw_values = {
        "has_readme": bool(readme_files),
        "has_tests": bool(test_files),
        "has_ci_cd": bool(ci_cd_files),
        "has_docker": bool(docker_files),
        "has_env_example": bool(env_example_files),
        "has_dependency_manifest": bool(dependency_files),
        "has_clear_structure": len(found_structure_markers) >= 2,
    }

    total_weight = sum(item["weight"] for item in QUALITY_CRITERIA.values())
    earned_weight = sum(
        QUALITY_CRITERIA[key]["weight"]
        for key, value in raw_values.items()
        if value
    )
    score = round((earned_weight / total_weight) * 10, 1) if total_weight else 0.0

    criteria: dict[str, dict[str, Any]] = {}
    for key, value in raw_values.items():
        config = QUALITY_CRITERIA[key]
        criteria[key] = {
            "value": value,
            "label": config["label_true"] if value else config["label_false"],
            "description": (
                config["description_true"] if value else config["description_false"]
            ),
        }

    return {
        "score": score,
        "max_score": 10,
        "score_label": _score_label(score),
        "criteria": criteria,
        "detected_files": {
            "readme": readme_files[:10],
            "tests": test_files[:20],
            "ci_cd": ci_cd_files[:10],
            "docker": docker_files[:10],
            "env_examples": env_example_files[:10],
            "dependency_manifests": dependency_files[:10],
        },
        "structure_markers": found_structure_markers,
    }


def build_default_quality_assessment(
    quality_facts: dict[str, Any],
) -> dict[str, Any]:
    criteria = quality_facts["criteria"]
    positives = [item["label"] for item in criteria.values() if item["value"]]
    negatives = [item["label"] for item in criteria.values() if not item["value"]]

    strengths = positives or ["В доступных данных есть базовая информация о репозитории."]
    risks = negatives or ["Существенные инфраструктурные риски по базовым признакам не обнаружены."]

    recommendations: list[str] = []
    if not criteria["has_tests"]["value"]:
        recommendations.append("Добавить unit-тесты и интеграционные тесты для ключевой логики.")
    if not criteria["has_ci_cd"]["value"]:
        recommendations.append("Добавить CI/CD workflow для автоматических проверок.")
    if not criteria["has_docker"]["value"]:
        recommendations.append("Добавить Dockerfile или docker-compose.yml для воспроизводимого запуска.")
    if not criteria["has_readme"]["value"]:
        recommendations.append("Добавить README с описанием запуска и структуры проекта.")
    if not recommendations:
        recommendations.append("Расширить тестовое покрытие и техническую документацию проекта.")

    return {
        "score": quality_facts["score"],
        "max_score": quality_facts["max_score"],
        "score_label": quality_facts["score_label"],
        "summary": (
            "Оценка сформирована на основе базовых признаков репозитория: README, "
            "тесты, CI/CD, Docker, пример переменных окружения, файлы зависимостей "
            "и понятность структуры проекта."
        ),
        "criteria": criteria,
        "strengths": strengths,
        "risks": risks,
        "recommendations": recommendations,
    }


def normalize_quality_assessment(
    llm_assessment: Any,
    quality_facts: dict[str, Any],
) -> dict[str, Any]:
    default_assessment = build_default_quality_assessment(quality_facts)

    if not isinstance(llm_assessment, dict):
        return default_assessment

    assessment = {
        "score": quality_facts["score"],
        "max_score": quality_facts["max_score"],
        "score_label": quality_facts["score_label"],
        "summary": llm_assessment.get("summary") or default_assessment["summary"],
        "criteria": quality_facts["criteria"],
        "strengths": llm_assessment.get("strengths") or default_assessment["strengths"],
        "risks": llm_assessment.get("risks") or default_assessment["risks"],
        "recommendations": (
            llm_assessment.get("recommendations")
            or default_assessment["recommendations"]
        ),
    }

    return assessment
