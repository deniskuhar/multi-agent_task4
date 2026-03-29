from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import trafilatura
from ddgs import DDGS

from config import get_settings

settings = get_settings()
OUTPUT_DIR = Path(__file__).resolve().parent / settings.output_dir
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n\n[truncated]"


def write_report(filename: str, content: str) -> str:
    safe_name = Path(filename).name or settings.default_report_name
    if not safe_name.endswith(".md"):
        safe_name += ".md"
    path = OUTPUT_DIR / safe_name
    path.write_text(content, encoding="utf-8")
    relative_path = path.relative_to(Path(__file__).resolve().parent)
    return f"Report saved to {relative_path.as_posix()}"


def web_search(query: str) -> list[dict[str, str]]:
    results = DDGS().text(query, max_results=settings.max_search_results)
    formatted: list[dict[str, str]] = []
    total_length = 0
    for item in results:
        entry = {
            "title": item.get("title", ""),
            "url": item.get("href", ""),
            "snippet": item.get("body", ""),
        }
        serialized = json.dumps(entry, ensure_ascii=False)
        total_length += len(serialized)
        if total_length > settings.max_search_content_length and formatted:
            break
        formatted.append(entry)
    return formatted


def read_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return f"Error: invalid URL '{url}'"

    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return f"Error: failed to download {url}"

    extracted = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=False,
        no_fallback=False,
    )
    if not extracted:
        return f"Error: could not extract readable text from {url}"

    return _truncate(extracted, settings.max_url_content_length)


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for relevant pages and return a short list of titles, URLs, and snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query describing the topic to investigate.",
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_url",
            "description": "Download and extract the main readable text from a URL for deeper analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the page that should be read.",
                    }
                },
                "required": ["url"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_report",
            "description": "Save the final Markdown report to a file in the output directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Filename for the markdown report, for example rag_comparison.md",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full Markdown content that should be saved.",
                    },
                },
                "required": ["filename", "content"],
                "additionalProperties": False,
            },
        },
    },
]


TOOL_REGISTRY = {
    "web_search": web_search,
    "read_url": read_url,
    "write_report": write_report,
}


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    tool = TOOL_REGISTRY.get(name)
    if tool is None:
        return f"Error: unknown tool '{name}'"

    try:
        result = tool(**arguments)
    except Exception as exc:
        return f"Error while executing {name}: {exc}"

    if isinstance(result, str):
        return result

    try:
        return json.dumps(result, ensure_ascii=False, indent=2)
    except TypeError:
        return str(result)
