"""HTTP client wrapper for the Mem0 memory backend."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any, Iterable

import httpx

from .config import SETTINGS
from .instrumentation import get_correlation_id, logger


class Mem0Error(RuntimeError):
    """Raised when the Mem0 backend returns an error response."""


@dataclass(slots=True)
class Mem0Client:
    """Thin wrapper around the Mem0 REST API."""

    base_url: str
    api_key: str | None = None
    timeout: float = 10.0

    def __post_init__(self) -> None:
        base = self.base_url.rstrip("/")
        if not base:
            raise ValueError("mem0 base url must be configured")
        self.base_url = base
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    # --- public helpers -------------------------------------------------
    def memory_search(
        self,
        *,
        query: str,
        user_id: str,
        limit: int,
        scopes: Iterable[str] | None,
    ) -> list[dict[str, Any]]:
        payload = {"query": query, "user_id": user_id, "limit": limit}
        if scopes is not None:
            payload["scopes"] = list(scopes)
        data = self._request("POST", "/memories/search", json=payload)
        return list(data.get("results", []))

    def memory_add(
        self,
        *,
        user_id: str,
        memory: str,
        scope: str,
        tags: Iterable[str] | None,
        source: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"user_id": user_id, "memory": memory, "scope": scope}
        if tags is not None:
            payload["tags"] = list(tags)
        if source:
            payload["source"] = source
        return self._request("POST", "/memories", json=payload)

    def memory_delete(self, *, memory_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/memories/{memory_id}")

    def memory_list(
        self,
        *,
        user_id: str,
        limit: int,
        scope: str | None = None,
        tags: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"user_id": user_id, "limit": limit}
        if scope:
            params["scope"] = scope
        if tags is not None:
            params["tags"] = ",".join(tags)
        data = self._request("GET", "/memories", params=params)
        return list(data.get("results", []))

    # --- internal helpers -----------------------------------------------
    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        correlation_id = get_correlation_id()
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not path.startswith("/"):
            path = "/" + path
        try:
            response = self._client.request(
                method,
                path,
                json=json,
                params=params,
                headers=self._headers(),
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network failure
            logger.error(
                "mem0.request_failed",
                status_code=exc.response.status_code,
                body=exc.response.text,
                method=method,
                path=path,
            )
            raise Mem0Error(
                f"Mem0 request failed with status {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:  # pragma: no cover - network failure
            logger.error("mem0.request_error", error=str(exc), method=method, path=path)
            raise Mem0Error(f"Mem0 request error: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:  # pragma: no cover - depends on remote response
            raise Mem0Error("Mem0 response did not contain valid JSON") from exc
        return data if isinstance(data, dict) else {"results": data}


_mem0_client: Mem0Client | None = None
_mem0_client_lock = Lock()


def build_mem0_client() -> Mem0Client:
    if SETTINGS.mem0_base_url is None:
        raise RuntimeError("MEM0_BASE_URL is not configured")
    return Mem0Client(base_url=SETTINGS.mem0_base_url, api_key=SETTINGS.mem0_api_key)


def get_mem0_client() -> Mem0Client:
    """Thread-safe singleton accessor for the Mem0 client."""
    global _mem0_client
    if _mem0_client is None:
        with _mem0_client_lock:
            # Double-check pattern
            if _mem0_client is None:
                _mem0_client = build_mem0_client()
    return _mem0_client


def set_mem0_client(client: Mem0Client | None) -> None:
    """Thread-safe setter for the Mem0 client (used in tests)."""
    global _mem0_client
    with _mem0_client_lock:
        _mem0_client = client
