"""
FastMCP adapter for the CORE RAG API.

This MCP server intentionally does not implement its own RAG engine.
It is a thin adapter over the FastAPI RAG service so Pi, MCP clients,
the CLI, and the scanner all use the same source of truth:

    scanner -> ChromaDB rag_directory_scanner -> /rag/query -> MCP tools
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastmcp import FastMCP

mcp = FastMCP("core-rag-api-adapter")

RAG_API_BASE_URL = os.getenv("RAG_API_BASE_URL", "http://localhost:8000").rstrip("/")
DEFAULT_TIMEOUT = float(os.getenv("RAG_API_TIMEOUT", "30"))


def _request_json(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Call the local RAG API and return parsed JSON."""
    url = f"{RAG_API_BASE_URL}{path}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(url, data=body, method=method.upper())
    req.add_header("Content-Type", "application/json")

    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"RAG API HTTP {exc.code} for {path}: {details}") from exc
    except URLError as exc:
        raise RuntimeError(f"RAG API unavailable at {RAG_API_BASE_URL}: {exc}") from exc


def _format_sources(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return "No sources returned."

    lines: list[str] = []
    for i, source in enumerate(sources, 1):
        filename = source.get("filename") or Path(source.get("source", "")).name or "unknown"
        source_path = source.get("source", "")
        score = source.get("score")
        text = source.get("text", "")

        score_line = f"Score: {score:.4f}" if isinstance(score, (int, float)) else "Score: n/a"
        lines.append(
            f"Result {i}: {filename}\n"
            f"Source: {source_path}\n"
            f"{score_line}\n"
            f"Text:\n{text}"
        )
    return "\n\n---\n\n".join(lines)


@mcp.tool()
async def search(query: str, top_k: int = 5) -> str:
    """
    Search indexed CORE/RAG documents through the RAG API.

    Args:
        query: Search query string.
        top_k: Number of results to return.

    Returns:
        Formatted source snippets from /rag/query.
    """
    try:
        data = _request_json("POST", "/rag/query", {"query": query, "top_k": top_k})
        return _format_sources(data.get("sources", []))
    except Exception as exc:
        return f"Search error: {exc}"


@mcp.tool()
async def ask(question: str, context: str = "") -> str:
    """
    Ask a question through the RAG API.

    Args:
        question: The question to answer.
        context: Optional extra context prepended to the question.

    Returns:
        Answer from /rag/query plus source summary.
    """
    try:
        query = f"{context}\n\n{question}" if context else question
        data = _request_json("POST", "/rag/query", {"query": query, "top_k": 5})
        answer = data.get("answer", "")
        sources = data.get("sources", [])
        return f"{answer}\n\nSources:\n{_format_sources(sources)}"
    except Exception as exc:
        return f"Answer error: {exc}"


@mcp.tool()
async def add_document(file_path: str) -> str:
    """
    Add a file directly to the RAG API index.

    This writes to the same ChromaDB collection used by the scanner.

    Args:
        file_path: Path to a text-like document file.

    Returns:
        Status message from /rag/index.
    """
    try:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return f"Error adding document: file not found: {path}"
        if not path.is_file():
            return f"Error adding document: not a file: {path}"

        text = path.read_text(encoding="utf-8")
        payload = {
            "id": str(path),
            "text": text,
            "metadata": {
                "source": str(path),
                "filename": path.name,
                "ingest_method": "mcp_add_document",
            },
        }
        data = _request_json("POST", "/rag/index", payload)
        return f"Document indexed via RAG API: {data}"
    except Exception as exc:
        return f"Error adding document: {exc}"


@mcp.tool()
async def list_documents() -> str:
    """
    List files tracked by the RAG scanner state.

    Returns:
        Formatted list of indexed/scanned source files.
    """
    try:
        state_path = Path("./ai_workspace/memory/index_state.json")
        if not state_path.exists():
            fallback = Path("./memory/index_state.json")
            state_path = fallback if fallback.exists() else state_path

        if not state_path.exists():
            return "No scanner state file found. Start the RAG API/scanner first."

        state = json.loads(state_path.read_text(encoding="utf-8"))
        files = sorted(state.get("files", {}).keys())
        if not files:
            return "No documents tracked by scanner."

        lines = [f"Tracked documents: {len(files)}", f"Last scan: {state.get('last_scan')}", ""]
        lines.extend(f"- {file_path}" for file_path in files)
        return "\n".join(lines)
    except Exception as exc:
        return f"Error listing documents: {exc}"


@mcp.tool()
async def health_check() -> dict[str, Any]:
    """
    Check health of the RAG API and scanner.

    Returns:
        Health status dictionary.
    """
    result: dict[str, Any] = {
        "status": "unknown",
        "rag_api_base_url": RAG_API_BASE_URL,
    }

    try:
        result["health"] = _request_json("GET", "/health", timeout=10)
        result["scanner"] = _request_json("GET", "/scanner/status", timeout=10)
        api_status = result["health"].get("status", "unknown")
        scanner_running = result["scanner"].get("scanner_running", False)
        result["status"] = "healthy" if scanner_running and api_status in {"healthy", "degraded"} else "degraded"
    except Exception as exc:
        result["status"] = "unhealthy"
        result["error"] = str(exc)

    return result


if __name__ == "__main__":
    mcp.run()
