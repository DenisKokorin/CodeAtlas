import os
from urllib.parse import quote, urlparse

import httpx
from fastapi import HTTPException


GITHUB_API_URL = "https://api.github.com"


def parse_github_repo_url(repo_url: str) -> tuple[str, str]:
    parsed_url = urlparse(repo_url.strip())

    if parsed_url.netloc.lower() != "github.com":
        raise HTTPException(
            status_code=400,
            detail="Repository URL must be a GitHub URL",
        )

    path_parts = [part for part in parsed_url.path.strip("/").split("/") if part]

    if len(path_parts) < 2:
        raise HTTPException(
            status_code=400,
            detail="Repository URL must contain owner and repository name",
        )

    return path_parts[0], path_parts[1].removesuffix(".git")


def normalize_repository_info(data: dict) -> dict:
    return {
        "full_name": data.get("full_name"),
        "html_url": data.get("html_url"),
        "description": data.get("description"),
        "language": data.get("language"),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "open_issues": data.get("open_issues_count", 0),
        "default_branch": data.get("default_branch"),
        "updated_at": data.get("updated_at"),
    }


def build_github_headers(accept: str = "application/vnd.github+json") -> dict:
    headers = {
        "Accept": accept,
        "User-Agent": "CodeAtlas",
    }

    github_token = os.getenv("GITHUB_API_TOKEN")

    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    return headers


def raise_github_api_error(response: httpx.Response, fallback_detail: str) -> None:
    """Raise a user-facing HTTPException for GitHub API errors."""
    github_message = ""

    try:
        payload = response.json()
        github_message = str(payload.get("message") or "")
    except ValueError:
        github_message = response.text.strip()[:300]

    rate_remaining = response.headers.get("X-RateLimit-Remaining")
    rate_reset = response.headers.get("X-RateLimit-Reset")

    if response.status_code == 403 and rate_remaining == "0":
        detail = (
            "GitHub API rate limit exceeded. Add GITHUB_API_TOKEN to backend/.env "
            "or try again later."
        )
        if rate_reset:
            detail += f" Rate limit reset timestamp: {rate_reset}."
    elif response.status_code == 403:
        detail = (
            "GitHub API access denied. Check repository access and GITHUB_API_TOKEN."
        )
    elif response.status_code == 404:
        detail = "GitHub repository not found or not accessible."
    else:
        detail = fallback_detail

    if github_message and github_message.lower() not in detail.lower():
        detail = f"{detail} GitHub message: {github_message}"

    raise HTTPException(status_code=response.status_code, detail=detail)


async def fetch_repository_info(repo_url: str) -> dict:
    owner, repository = parse_github_repo_url(repo_url)

    headers = build_github_headers()
    url = f"{GITHUB_API_URL}/repos/{owner}/{repository}"
    timeout = httpx.Timeout(8.0, connect=4.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        last_error: httpx.HTTPError | None = None

        for _ in range(3):
            try:
                response = await client.get(url, headers=headers)

                if response.status_code in {403, 404}:
                    raise_github_api_error(
                        response=response,
                        fallback_detail="Unable to fetch repository info from GitHub",
                    )

                response.raise_for_status()

                return normalize_repository_info(response.json())
            except httpx.HTTPStatusError as exc:
                last_error = exc

                if exc.response.status_code < 500:
                    break
            except httpx.HTTPError as exc:
                last_error = exc

    raise HTTPException(
        status_code=502,
        detail="Unable to fetch repository info from GitHub",
    ) from last_error


async def fetch_repository_tree(
    repo_url: str,
    branch: str,
    max_items: int = 120,
) -> list[dict]:
    owner, repository = parse_github_repo_url(repo_url)

    headers = build_github_headers()
    encoded_branch = quote(branch, safe="")
    url = (
        f"{GITHUB_API_URL}/repos/{owner}/{repository}/git/trees/"
        f"{encoded_branch}?recursive=1"
    )
    timeout = httpx.Timeout(10.0, connect=4.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers=headers)

    if response.status_code in {403, 404}:
        raise_github_api_error(
            response=response,
            fallback_detail="Unable to fetch repository tree from GitHub",
        )

    response.raise_for_status()

    tree = response.json().get("tree", [])
    normalized_tree = []

    for item in tree[:max_items]:
        normalized_tree.append(
            {
                "path": item.get("path"),
                "type": item.get("type"),
                "size": item.get("size"),
            }
        )

    return normalized_tree


async def fetch_repository_file_text(
    repo_url: str,
    branch: str,
    path: str,
    max_chars: int,
) -> str | None:
    owner, repository = parse_github_repo_url(repo_url)

    headers = build_github_headers("application/vnd.github.raw")
    encoded_path = quote(path, safe="/")
    url = (
        f"{GITHUB_API_URL}/repos/{owner}/{repository}/contents/"
        f"{encoded_path}?ref={quote(branch, safe='')}"
    )
    timeout = httpx.Timeout(10.0, connect=4.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers=headers)

    if response.status_code == 404:
        return None

    if response.status_code == 403:
        raise_github_api_error(
            response=response,
            fallback_detail="Unable to fetch repository file from GitHub",
        )

    response.raise_for_status()

    text = response.text

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "\n\n[Текст файла обрезан из-за ограничения размера.]"
