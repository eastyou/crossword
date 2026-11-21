"""A4 可打印填字游戏 HTML 渲染。"""

from __future__ import annotations

import html
from typing import Dict, List, Tuple

from .model import Cell, CrosswordError, Grid

DIRECTION_LABELS: Dict[str, str] = {"across": "横向", "down": "纵向"}

PAGE_CSS: str = """
@page { size: A4; margin: 0 }
* { box-sizing: border-box }
body {
  margin: 0;
  background: #eef1f5;
  color: #1f2328;
  font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", Arial, sans-serif;
}
.page {
  width: 210mm;
  min-height: 297mm;
  padding: 12mm;
  box-sizing: border-box;
  overflow: hidden;
  background: #ffffff;
  margin: 0 auto 8mm;
  display: flex;
  flex-direction: column;
  page-break-after: always;
}
.page:last-child { page-break-after: auto; margin-bottom: 0 }
.doc-header { text-align: center; margin-bottom: 5mm }
.doc-header h1 { font-size: 22pt; letter-spacing: 2px; margin: 0 0 2mm }
.doc-header .tip { font-size: 9.5pt; color: #5b6470; margin: 0; line-height: 1.6 }
.grid-wrap { display: flex; justify-content: center; margin: 3mm 0 5mm }
table.grid { border-collapse: collapse; table-layout: fixed }
table.grid td { padding: 0 }
table.grid td.cell {
  position: relative;
  border: 0.45mm solid #1f2328;
  text-align: left;
  vertical-align: top;
}
table.grid td.blank { border: none }
table.grid .num {
  position: absolute;
  top: 0.2mm;
  left: 0.6mm;
  font-size: 2.2mm;
  line-height: 1;
  color: #6b7280;
  font-family: Arial, Helvetica, sans-serif;
}
table.grid .letter {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  line-height: 1;
}
.clues { display: grid; grid-template-columns: 1fr 1fr; column-gap: 8mm }
.clues section h2 {
  font-size: 11pt;
  margin: 0 0 2mm;
  padding-bottom: 1mm;
  border-bottom: 0.3mm solid #d0d5dd;
}
.clues ul { margin: 0; padding: 0; list-style: none }
.clues li { font-size: 9.5pt; line-height: 1.5; margin-bottom: 1.4mm; break-inside: avoid }
.clues .idx { font-weight: 700; margin-right: 1.5mm }
.words { margin-top: 2mm }
.words h2 { font-size: 11pt; margin: 0 0 2mm; border-bottom: 0.3mm solid #d0d5dd; padding-bottom: 1mm }
.words table { width: 100%; border-collapse: collapse; font-size: 9.5pt }
.words th, .words td { border: 0.25mm solid #c8ced8; padding: 1.2mm 1.6mm; text-align: left }
.words th { background: #f2f4f7 }
.words td.answer { font-weight: 600; letter-spacing: 1px }
.doc-footer { margin-top: auto; padding-top: 4mm; text-align: center; color: #98a2b3; font-size: 8pt }
@media print {
  body { background: #ffffff }
  .page { margin: 0 }
}
"""


def _document(pages: List[str], title: str) -> str:
    """把若干页面拼成完整的 HTML 文档。"""
    safe_title = html.escape(title)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh-CN">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{safe_title}</title>\n"
        f"<style>{PAGE_CSS}</style>\n"
        "</head>\n<body>\n"
        + "\n".join(pages)
        + "\n</body>\n</html>\n"
    )


def _validate_grid(grid: Grid, numbers: Dict[Cell, int]) -> None:
    """校验渲染所需的网格与编号参数。"""
    if not isinstance(grid, Grid):
        raise CrosswordError("grid 参数必须是 Grid 实例")
    if not isinstance(numbers, dict):
        raise CrosswordError("numbers 参数必须是字典")
    if grid.width <= 0 or grid.height <= 0 or not grid.cells:
        raise CrosswordError("网格为空，无法渲染")


def _grid_html(grid: Grid, numbers: Dict[Cell, int], show_letters: bool) -> str:
    """渲染网格表格，show_letters 控制是否显示答案字母。"""
    available_width = 186.0 * 0.98
    available_height = 118.0
    cell_mm = min(available_width / grid.width, available_height / grid.height)
    cell_mm = max(4.2, min(cell_mm, 16.0))
    font_mm = max(1.8, cell_mm * 0.5)

    rows: List[str] = []
    for row in range(grid.height):
        cells: List[str] = []
        for col in range(grid.width):
            letter = grid.cells.get((row, col))
            if letter is None:
                cells.append(
                    f'<td class="blank" style="width:{cell_mm:.2f}mm;'
                    f'height:{cell_mm:.2f}mm"></td>'
                )
                continue
            number = numbers.get((row, col))
            number_html = f'<span class="num">{number}</span>' if number else ""
            letter_html = html.escape(letter) if show_letters else ""
            cells.append(
                f'<td class="cell" style="width:{cell_mm:.2f}mm;'
                f'height:{cell_mm:.2f}mm">'
                f'{number_html}<span class="letter">{letter_html}</span></td>'
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")

    return (
        '<div class="grid-wrap">'
        f'<table class="grid" style="width:{cell_mm * grid.width:.2f}mm;'
        f'font-size:{font_mm:.2f}mm">'
        + "".join(rows)
        + "</table></div>"
    )


def _clue_groups(grid: Grid, numbers: Dict[Cell, int]) -> Tuple[List[Tuple[int, str, int]], List[Tuple[int, str, int]]]:
    """按方向把词条整理为 (编号, 线索, 字数) 列表。"""
    across: List[Tuple[int, str, int]] = []
    down: List[Tuple[int, str, int]] = []
    for item in grid.placed:
        number = numbers.get((item.row, item.col))
        if number is None:
            continue
        target = across if item.direction == "across" else down
        target.append((number, item.entry.clue, len(item.entry.answer)))
    across.sort(key=lambda value: value[0])
    down.sort(key=lambda value: value[0])
    return across, down


def _clue_section(label: str, clues: List[Tuple[int, str, int]]) -> str:
    """渲染一组线索。"""
    if clues:
        items = "".join(
            f'<li><span class="idx">{number}.</span>'
            f"{html.escape(clue)}（{length} 字）</li>"
            for number, clue, length in clues
        )
        return f'<section><h2>{label}</h2><ul>{items}</ul></section>'
    return f'<section><h2>{label}</h2><ul><li>（无）</li></ul></section>'


def _header(title: str, tip: str) -> str:
    """渲染页面标题与说明。"""
    return (
        '<div class="doc-header">'
        f"<h1>{html.escape(title)}</h1>"
        f'<p class="tip">{tip}</p>'
        "</div>"
    )


def _footer() -> str:
    """渲染页脚。"""
    return '<div class="doc-footer">crossword · A4 打印版</div>'


def _puzzle_page(grid: Grid, numbers: Dict[Cell, int], title: str) -> str:
    """渲染题面页。"""
    _validate_grid(grid, numbers)
    across, down = _clue_groups(grid, numbers)
    tip = "根据线索，在空白格中填入对应词语，每个字符占一格；横向与纵向交叉处的字符需一致。"
    return (
        '<div class="page">'
        + _header(title, tip)
        + _grid_html(grid, numbers, show_letters=False)
        + '<div class="clues">'
        + _clue_section("横向", across)
        + _clue_section("纵向", down)
        + "</div>"
        + _footer()
        + "</div>"
    )


def _answers_page(grid: Grid, numbers: Dict[Cell, int], title: str) -> str:
    """渲染答案页。"""
    _validate_grid(grid, numbers)
    across, down = _clue_groups(grid, numbers)
    word_items: List[Tuple[int, str, str, str]] = []
    for word in grid.placed:
        number = numbers.get((word.row, word.col))
        if number is None:
            continue
        word_items.append(
            (
                number,
                word.direction,
                word.entry.answer,
                word.entry.clue,
            )
        )
    word_items.sort(key=lambda value: (value[0], 0 if value[1] == "across" else 1))
    word_rows: List[str] = []
    for number, direction, answer, clue in word_items:
        word_rows.append(
            "<tr>"
            f"<td>{number}</td>"
            f"<td>{DIRECTION_LABELS[direction]}</td>"
            f'<td class="answer">{html.escape(answer)}</td>'
            f"<td>{html.escape(clue)}</td>"
            "</tr>"
        )
    table = (
        '<div class="words"><h2>完整词表</h2><table>'
        "<thead><tr><th>编号</th><th>方向</th><th>答案</th><th>线索</th></tr></thead>"
        "<tbody>" + "".join(word_rows) + "</tbody></table></div>"
    )
    return (
        '<div class="page">'
        + _header(f"{title} · 参考答案", "答案页：核对填字结果与完整词表。")
        + _grid_html(grid, numbers, show_letters=True)
        + '<div class="clues">'
        + _clue_section("横向", across)
        + _clue_section("纵向", down)
        + "</div>"
        + table
        + _footer()
        + "</div>"
    )


def render_puzzle(grid: Grid, numbers: Dict[Cell, int], title: str = "填字游戏") -> str:
    """渲染题面 HTML（A4 单页）。

    Args:
        grid: 已排布的网格。
        numbers: 编号映射。
        title: 题面标题。

    Returns:
        完整的 HTML 字符串。

    Raises:
        CrosswordError: 网格为空或参数类型错误时抛出。
    """
    return _document([_puzzle_page(grid, numbers, title)], title)


def render_answers(grid: Grid, numbers: Dict[Cell, int]) -> str:
    """渲染答案页 HTML（A4 单页）。

    Args:
        grid: 已排布的网格。
        numbers: 编号映射。

    Returns:
        完整的 HTML 字符串。

    Raises:
        CrosswordError: 网格为空或参数类型错误时抛出。
    """
    return _document([_answers_page(grid, numbers, "填字游戏")], "填字游戏 · 参考答案")


def render_document(
    grid: Grid,
    numbers: Dict[Cell, int],
    title: str = "填字游戏",
    show_answers: bool = True,
) -> str:
    """拼合题面与答案页（各自独立分页）。

    Args:
        grid: 已排布的网格。
        numbers: 编号映射。
        title: 题面标题。
        show_answers: 是否附加答案页。

    Returns:
        完整的 HTML 字符串。

    Raises:
        CrosswordError: 网格为空或参数类型错误时抛出。
    """
    if not isinstance(title, str):
        raise CrosswordError("标题必须是文本")
    pages = [_puzzle_page(grid, numbers, title)]
    if show_answers:
        pages.append(_answers_page(grid, numbers, title))
    return _document(pages, title)


__all__ = ["render_puzzle", "render_answers", "render_document"]
