"""Document chunking utilities following the PRD recommendations."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .documents import DocumentChunk, DocumentMetadata

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path
    import tiktoken

CHUNK_SIZE_TOKENS = 800
CHUNK_OVERLAP_TOKENS = 200

tokenizer_cache: dict[str, Any] = {}


def _get_tiktoken():
    spec = importlib.util.find_spec("tiktoken")
    if spec is None:  # pragma: no cover - optional dependency
        class _FallbackEncoding:
            def encode(self, text: str) -> list[int]:
                return list(text.encode("utf-8"))

            def decode(self, tokens: list[int]) -> str:
                return bytes(tokens).decode("utf-8", errors="ignore")

        class _FallbackTiktoken:
            def encoding_for_model(self, _model: str) -> _FallbackEncoding:
                return _FallbackEncoding()

        return _FallbackTiktoken()
    import tiktoken

    return tiktoken


def _encoding_for_model(model: str) -> tiktoken.Encoding:
    tiktoken = _get_tiktoken()
    if model not in tokenizer_cache:
        tokenizer_cache[model] = tiktoken.encoding_for_model(model)
    return tokenizer_cache[model]


@dataclass
class ChunkingResult:
    chunks: list[DocumentChunk]
    token_count: int


def chunk_text(
    metadata: DocumentMetadata,
    text: str,
    model: str,
) -> ChunkingResult:
    """Chunks text into overlapping fragments based on token counts."""
    encoding = _encoding_for_model(model)
    tokens = encoding.encode(text)
    token_count = len(tokens)

    if not tokens:
        return ChunkingResult(chunks=[], token_count=0)

    # First pass: determine chunk boundaries to get the real chunk count
    boundaries: list[tuple[int, int]] = []
    start = 0
    while True:
        end = min(token_count, start + CHUNK_SIZE_TOKENS)
        boundaries.append((start, end))
        if end >= token_count:
            break
        start += CHUNK_SIZE_TOKENS - CHUNK_OVERLAP_TOKENS

    chunk_count = len(boundaries)

    # Second pass: create the chunks with the correct metadata
    chunks: list[DocumentChunk] = []
    for i, (start, end) in enumerate(boundaries):
        chunk_tokens = tokens[start:end]
        chunk_text_str = encoding.decode(chunk_tokens)
        chunk_id = f"{metadata.document_id}:{i}"
        chunks.append(
            DocumentChunk(
                id=chunk_id,
                text=chunk_text_str,
                metadata=metadata,
                chunk_index=i,
                chunk_count=chunk_count,
            )
        )

    return ChunkingResult(chunks=chunks, token_count=token_count)


def read_text(path: Path) -> str:
    data = path.read_text(encoding="utf-8")
    return data.replace("\r\n", "\n")


def supported_suffix(path: Path) -> bool:
    return path.suffix.lower() == ".md"


def iter_documents(input_dir: Path) -> Iterable[Path]:
    for path in input_dir.rglob("*"):
        if path.name.startswith("."):
            continue
        if path.is_file() and supported_suffix(path):
            yield path
