"""Generate lightweight SVG research figures from tabular outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_heatmap_svg(
    frame: pd.DataFrame,
    *,
    row: str,
    column: str,
    value: str,
    output: str | Path,
    title: str,
) -> None:
    """Write a compact SVG heatmap from long-form data."""
    rows = sorted(frame[row].astype(str).unique())
    columns = sorted(frame[column].astype(str).unique())
    cell = 42
    width = 160 + cell * len(columns)
    height = 90 + cell * len(rows)
    lookup = {
        (str(item[row]), str(item[column])): float(item[value])
        for item in frame.to_dict(orient="records")
        if pd.notna(item[value])
    }
    parts = [_svg_header(width, height, title)]
    for col_index, name in enumerate(columns):
        parts.append(_text(140 + col_index * cell, 50, name, 10))
    for row_index, name in enumerate(rows):
        parts.append(_text(10, 85 + row_index * cell, name, 10))
        for col_index, col_name in enumerate(columns):
            score = max(0.0, min(1.0, lookup.get((name, col_name), 0.0)))
            shade = int(245 - 170 * score)
            parts.append(
                f'<rect x="{130 + col_index * cell}" y="{65 + row_index * cell}" '
                f'width="{cell - 3}" height="{cell - 3}" fill="rgb({shade},{shade},245)" />'
            )
    parts.append("</svg>")
    _write(output, "\n".join(parts))


def write_bar_svg(
    frame: pd.DataFrame,
    *,
    label: str,
    value: str,
    output: str | Path,
    title: str,
) -> None:
    """Write a compact SVG horizontal bar chart."""
    data = frame[[label, value]].copy()
    data[value] = pd.to_numeric(data[value], errors="coerce").fillna(0.0)
    width = 640
    height = 80 + 28 * len(data)
    max_value = float(data[value].max()) if not data.empty else 1.0
    max_value = max(max_value, 1e-12)
    parts = [_svg_header(width, height, title)]
    for index, item in enumerate(data.to_dict(orient="records")):
        y = 60 + index * 28
        bar_width = int(420 * float(item[value]) / max_value)
        parts.append(_text(10, y + 14, str(item[label]), 11))
        parts.append(
            f'<rect x="190" y="{y}" width="{bar_width}" height="18" fill="#4169e1" />'
        )
        parts.append(_text(620, y + 14, f"{float(item[value]):.2f}", 10, anchor="end"))
    parts.append("</svg>")
    _write(output, "\n".join(parts))


def _svg_header(width: int, height: int, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        '<rect width="100%" height="100%" fill="white" />\n'
        f'{_text(10, 24, title, 14)}'
    )


def _text(x: int, y: int, text: str, size: int, *, anchor: str = "start") -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" '
        f'text-anchor="{anchor}" fill="#111">{_escape(text)}</text>'
    )


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _write(output: str | Path, content: str) -> None:
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
