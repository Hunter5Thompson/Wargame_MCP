"""Document chunking utilities following the PRD recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:  # pragma: no cover - optional dependency
    import tiktoken
except Exception:  # pragma: no cover - fallback when tiktoken is missing
    tiktoken = None  # type: ignore

from .documents import DocumentChunk, DocumentMetadata


CHUNK_SIZE_TOKENS = 800
CHUNK_OVERLAP_TOKENS = 200

tokenizer_cache: dict[str, Any] = {}


def _encoding_for_model(model: str):
    if tiktoken is None:
        return _SimpleEncoding()
    if model not in tokenizer_cache:
        tokenizer_cache[model] = tiktoken.encoding_for_model(model)
    return tokenizer_cache[model]


class _SimpleEncoding:  # pragma: no cover - fallback used in CI without tiktoken
    def encode(self, text: str) -> list[int]:
        return [ord(ch) for ch in text]

    def decode(self, tokens: Iterable[int]) -> str:
        return "".join(chr(int(token)) for token in tokens)


@dataclass
class ChunkingResult:
    chunks: list[DocumentChunk]
    token_count: int


def chunk_text(
    metadata: DocumentMetadata,
    text: str,
    model: str,
) -> ChunkingResult:
    encoding = _encoding_for_model(model)
    tokens = encoding.encode(text)
    chunks: list[DocumentChunk] = []
    token_count = len(tokens)
    chunk_count = max(1, (token_count + CHUNK_SIZE_TOKENS - 1) // (CHUNK_SIZE_TOKENS - CHUNK_OVERLAP_TOKENS))

    start = 0
    chunk_index = 0
    while start < token_count:
        end = min(token_count, start + CHUNK_SIZE_TOKENS)
        chunk_tokens = tokens[start:end]
        chunk_text_str = encoding.decode(chunk_tokens)
        chunk_id = f"{metadata.document_id}:{chunk_index}"
        chunks.append(
            DocumentChunk(
                id=chunk_id,
                text=chunk_text_str,
                metadata=metadata,
                chunk_index=chunk_index,
                chunk_count=chunk_count,
            )
        )
        if end == token_count:
            break
        start = max(0, end - CHUNK_OVERLAP_TOKENS)
        chunk_index += 1

    return ChunkingResult(chunks=chunks, token_count=token_count)


def read_text(path: Path) -> str:
    data = path.read_text(encoding="utf-8")
    return data.replace("\r\n", "\n")


def supported_suffix(path: Path) -> bool:
    return path.suffix.lower() in {".txt", ".md"}


def iter_documents(input_dir: Path) -> Iterable[Path]:
    for path in input_dir.rglob("*"):
        if path.is_file() and supported_suffix(path):
            yield path
