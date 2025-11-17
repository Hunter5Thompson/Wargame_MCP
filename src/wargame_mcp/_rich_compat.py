"""Small compatibility shim for environments without Rich installed."""

from __future__ import annotations

from dataclasses import dataclass, field

try:  # pragma: no cover - prefer the actual Rich classes when available
    from rich.console import Console as RichConsole
    from rich.table import Table as RichTable
except Exception:  # pragma: no cover - fallback for offline installs
    RichConsole = None  # type: ignore
    RichTable = None  # type: ignore


if RichConsole is not None and RichTable is not None:  # pragma: no cover - thin alias
    Console = RichConsole
    Table = RichTable
else:

    @dataclass
    class Table:  # pragma: no cover - simple text fallback
        title: str | None = None
        columns: list[str] = field(default_factory=list)
        rows: list[tuple[str, ...]] = field(default_factory=list)

        def add_column(self, name: str, **_kwargs) -> None:
            self.columns.append(name)

        def add_row(self, *values: str) -> None:
            self.rows.append(tuple(str(value) for value in values))

        def __str__(self) -> str:
            lines: list[str] = []
            if self.title:
                lines.append(self.title)
            if self.columns:
                header = " | ".join(self.columns)
                lines.append(header)
                lines.append("-" * len(header))
            for row in self.rows:
                lines.append(" | ".join(row))
            return "\n".join(lines)

    class Console:  # pragma: no cover - simple text fallback
        def print(self, *values, **_kwargs) -> None:
            text = " ".join(str(value) for value in values)
            print(text)

        def log(self, *values, **_kwargs) -> None:
            self.print(*values)


__all__ = ["Console", "Table"]
