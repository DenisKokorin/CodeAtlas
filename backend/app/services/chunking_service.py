"""
Document and code chunking service for RAG.

Chunking strategies:
- Documentation: Split markdown by headings (##, ###), 500-2000 chars per chunk
- Code: Split source files by function/class definitions
- Repository metadata: Single chunk with repo name, description, language
"""

import json
import os
import re
from typing import Any

DEFAULT_MIN_CHUNK_SIZE = 500
DEFAULT_MAX_CHUNK_SIZE = 2000

EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".php": "php",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
    ".rst": "markdown",
    ".sql": "sql",
    ".dockerfile": "dockerfile",
    ".tf": "hcl",
    ".css": "css",
    ".scss": "css",
    ".html": "html",
    ".vue": "vue",
    ".svelte": "svelte",
}

CODE_SPLIT_PATTERNS: dict[str, re.Pattern] = {
    "python": re.compile(
        r"^(async\s+)?def\s+\w+|^class\s+\w+", re.MULTILINE
    ),
    "javascript": re.compile(
        r"^(export\s+(default\s+)?)?(async\s+)?function(\s*\*)?\s+\w+|"
        r"^class\s+\w+|"
        r"^const\s+\w+\s*=\s*(async\s+)?\(|"
        r"^(export\s+)?(default\s+)?(function|class)\b",
        re.MULTILINE,
    ),
    "typescript": re.compile(
        r"^(export\s+(default\s+)?)?(async\s+)?function(\s*\*)?\s+\w+|"
        r"^class\s+\w+|"
        r"^const\s+\w+\s*=\s*(async\s+)?\(|"
        r"^(export\s+)?interface\s+\w+|"
        r"^(export\s+)?type\s+\w+\s*=",
        re.MULTILINE,
    ),
    "go": re.compile(
        r"^func\s+\w+|^type\s+\w+\s+struct|^type\s+\w+\s+interface", re.MULTILINE
    ),
    "java": re.compile(
        r"^(public|private|protected|static)?\s*(class|interface|enum)\s+\w+|"
        r"^(public|private|protected)?\s+\w+\s+\w+\s*\(",
        re.MULTILINE,
    ),
    "ruby": re.compile(
        r"^(def\s+\w+|class\s+\w+|module\s+\w+)", re.MULTILINE
    ),
    "rust": re.compile(
        r"^(fn\s+\w+|struct\s+\w+|enum\s+\w+|impl\s+|trait\s+\w+)", re.MULTILINE
    ),
}


def detect_language(file_path: str) -> str | None:
    """Detect programming language from file path/extension."""
    _, ext = os.path.splitext(file_path)
    ext_lower = ext.lower()
    basename = os.path.basename(file_path).lower()

    if basename == "dockerfile":
        return "dockerfile"
    if basename in ("makefile", "gnumakefile"):
        return "makefile"

    return EXTENSION_LANGUAGE_MAP.get(ext_lower)


def chunk_documentation(
    documentation_text: str,
    min_chars: int = DEFAULT_MIN_CHUNK_SIZE,
    max_chars: int = DEFAULT_MAX_CHUNK_SIZE,
) -> list[dict[str, Any]]:
    """
    Split markdown documentation into chunks by headings.

    Returns list of dicts:
      {content, source_path=None, chunk_type="documentation",
       metadata_json='{"heading": "...", "heading_level": 2}'}
    """
    if not documentation_text or not documentation_text.strip():
        return []

    heading_pattern = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)
    sections: list[dict[str, Any]] = []
    last_pos = 0
    last_heading = None
    last_level = 0
    heading_stack: list[tuple[int, str]] = []

    for match in heading_pattern.finditer(documentation_text):
        if last_pos > 0 or last_heading is not None:
            section_content = documentation_text[last_pos : match.start()].strip()
            heading_context = " > ".join(h for _, h in heading_stack)

            if last_heading:
                full_heading = f"{'#' * last_level} {last_heading}"
                content = f"{full_heading}\n\n{section_content}" if section_content else full_heading
            else:
                content = section_content

            metadata = {
                "heading": last_heading or "",
                "heading_level": last_level,
                "heading_context": heading_context,
            }

            sections.append({
                "content": content,
                "metadata": metadata,
            })

        while heading_stack and heading_stack[-1][0] >= len(match.group(1)):
            heading_stack.pop()

        heading_stack.append((len(match.group(1)), match.group(2)))
        last_pos = match.start()
        last_heading = match.group(2)
        last_level = len(match.group(1))

    if last_pos < len(documentation_text):
        section_content = documentation_text[last_pos:].strip()
        heading_context = " > ".join(h for _, h in heading_stack)

        if last_heading:
            full_heading = f"{'#' * last_level} {last_heading}"
            content = f"{full_heading}\n\n{section_content}" if section_content else full_heading
        else:
            content = section_content or documentation_text.strip()

        metadata = {
            "heading": last_heading or "",
            "heading_level": last_level,
            "heading_context": heading_context,
        }

        sections.append({
            "content": content,
            "metadata": metadata,
        })

    if not sections:
        sections.append({
            "content": documentation_text.strip(),
            "metadata": {"heading": "", "heading_level": 0, "heading_context": ""},
        })

    merged = _merge_sections(sections, min_chars, max_chars)

    return [
        {
            "content": s["content"],
            "source_path": None,
            "chunk_type": "documentation",
            "language": "markdown",
            "metadata_json": json.dumps(s["metadata"], ensure_ascii=False),
        }
        for s in merged
    ]


def _merge_sections(
    sections: list[dict[str, Any]],
    min_chars: int,
    max_chars: int,
) -> list[dict[str, Any]]:
    """Merge small sections together and split large ones."""
    if not sections:
        return []

    merged: list[dict[str, Any]] = []
    buffer = ""

    for section in sections:
        if not buffer:
            buffer = section["content"]
            continue

        candidate = buffer + "\n\n" + section["content"]

        if len(candidate) <= max_chars:
            buffer = candidate
        elif len(buffer) >= min_chars:
            merged.append({"content": buffer, "metadata": section["metadata"]})
            buffer = section["content"]
        else:
            merged.append({"content": candidate, "metadata": section["metadata"]})
            buffer = ""

    if buffer:
        merged.append({"content": buffer, "metadata": sections[-1]["metadata"]})

    for i, section in enumerate(merged):
        if len(section["content"]) > max_chars:
            parts = _split_long_text(section["content"], max_chars)
            merged[i : i + 1] = [
                {"content": p, "metadata": section["metadata"]} for p in parts
            ]

    return merged


def _split_long_text(text: str, max_chars: int) -> list[str]:
    """Split a long text into smaller chunks at paragraph boundaries."""
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if not current:
            current = para
        elif len(current) + 2 + len(para) <= max_chars:
            current += "\n\n" + para
        else:
            chunks.append(current)
            current = para

    if current:
        chunks.append(current)

    return chunks


def chunk_code_file(
    file_path: str,
    content: str,
    max_chars: int = DEFAULT_MAX_CHUNK_SIZE,
) -> list[dict[str, Any]]:
    """
    Split source code into chunks by function/class definitions.

    Returns list of dicts:
      {content, source_path, chunk_type="code", language,
       metadata_json='{"name": "...", "type": "function", "start_line": 10}'}
    """
    if not content or not content.strip():
        return []

    language = detect_language(file_path)
    pattern = CODE_SPLIT_PATTERNS.get(language) if language else None

    if pattern is None:
        for lang, pat in CODE_SPLIT_PATTERNS.items():
            if pat.search(content):
                language = lang
                pattern = pat
                break

    if pattern is None:
        return [
            {
                "content": content[:max_chars],
                "source_path": file_path,
                "chunk_type": "code",
                "language": language,
                "metadata_json": json.dumps({
                    "name": os.path.basename(file_path),
                    "type": "file",
                    "start_line": 1,
                }),
            }
        ]

    lines = content.split("\n")
    matches = list(pattern.finditer(content))
    chunks: list[dict[str, Any]] = []

    for i, match in enumerate(matches):
        start_pos = match.start()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        chunk_text = content[start_pos:end_pos].strip()

        if not chunk_text:
            continue

        if len(chunk_text) > max_chars:
            chunk_text = chunk_text[: max_chars - 100] + "\n\n[Код обрезан из-за ограничения размера.]"

        line_number = content[:start_pos].count("\n") + 1
        name_match = re.match(
            r"(?:async\s+|export\s+(?:default\s+)?)?(?:def|class|function|fun|fn|func|interface|type|struct|enum|trait|impl)\s+(\w+)",
            match.group(),
        )
        name = name_match.group(1) if name_match else os.path.basename(file_path)
        def_type = "class" if "class" in match.group() else "function"

        chunks.append({
            "content": chunk_text,
            "source_path": file_path,
            "chunk_type": "code",
            "language": language,
            "metadata_json": json.dumps({
                "name": name,
                "type": def_type,
                "start_line": line_number,
            }, ensure_ascii=False),
        })

    return chunks


def chunk_repository_metadata(
    name: str,
    repo_url: str,
    description: str | None = None,
    github_full_name: str | None = None,
    github_language: str | None = None,
    github_default_branch: str | None = None,
) -> dict[str, Any]:
    """
    Create a single metadata chunk with repository overview information.
    """
    parts: list[str] = []

    if github_full_name:
        parts.append(f"Repository: {github_full_name}")
    parts.append(f"URL: {repo_url}")
    if description:
        parts.append(f"Description: {description}")
    if github_language:
        parts.append(f"Primary Language: {github_language}")
    if github_default_branch:
        parts.append(f"Default Branch: {github_default_branch}")
    parts.append(f"Name: {name}")

    return {
        "content": "\n".join(parts),
        "source_path": None,
        "chunk_type": "repository_metadata",
        "language": None,
        "metadata_json": "{}",
    }