"""crossword：填字游戏生成器。"""

from __future__ import annotations

from .model import (
    CrosswordError,
    Entry,
    Grid,
    Placed,
    build_grid,
    demo_entries,
    grid_preview,
    is_valid_position,
    normalize_answer,
    number_cells,
    parse_csv_text,
    read_csv,
)

__all__ = [
    "CrosswordError",
    "Entry",
    "Grid",
    "Placed",
    "build_grid",
    "demo_entries",
    "grid_preview",
    "is_valid_position",
    "normalize_answer",
    "number_cells",
    "parse_csv_text",
    "read_csv",
]

__version__ = "0.1.0"
