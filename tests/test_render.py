"""render 模块单元测试：A4 题面、答案页与 HTML 转义。"""

from __future__ import annotations

import random
import unittest
from typing import Dict, List, Tuple

from crossword.model import CrosswordError, Entry, Grid, build_grid, number_cells
from crossword.render import render_answers, render_document, render_puzzle


def sample_grid() -> Tuple[Grid, Dict[Tuple[int, int], int]]:
    """构造一个稳定的小网格及其编号。"""
    entries: List[Entry] = [
        Entry("CAT", "猫咪"),
        Entry("ATOM", "原子"),
        Entry("OMEN", "征兆"),
        Entry("END", "结束"),
    ]
    grid = build_grid(entries, 9, random.Random(42))
    return grid, number_cells(grid)


class TestRenderPuzzle(unittest.TestCase):
    def test_document_structure(self) -> None:
        grid, numbers = sample_grid()
        page = render_puzzle(grid, numbers)
        self.assertTrue(page.startswith("<!DOCTYPE html>"))
        self.assertIn('<meta charset="utf-8">', page)
        self.assertIn("</html>", page)

    def test_default_title(self) -> None:
        grid, numbers = sample_grid()
        self.assertIn("<h1>填字游戏</h1>", render_puzzle(grid, numbers))

    def test_custom_title(self) -> None:
        grid, numbers = sample_grid()
        self.assertIn("<h1>期中复习</h1>", render_puzzle(grid, numbers, "期中复习"))

    def test_a4_css(self) -> None:
        grid, numbers = sample_grid()
        page = render_puzzle(grid, numbers)
        self.assertIn("@page { size: A4; margin: 0 }", page)
        self.assertIn("width: 210mm", page)
        self.assertIn("min-height: 297mm", page)
        self.assertIn("padding: 12mm", page)

    def test_all_cells_rendered(self) -> None:
        grid, numbers = sample_grid()
        page = render_puzzle(grid, numbers)
        self.assertEqual(page.count('<td class="cell"'), len(grid.cells))

    def test_numbers_rendered(self) -> None:
        grid, numbers = sample_grid()
        page = render_puzzle(grid, numbers)
        for number in numbers.values():
            self.assertIn(f'<span class="num">{number}</span>', page)

    def test_clues_rendered(self) -> None:
        grid, numbers = sample_grid()
        page = render_puzzle(grid, numbers)
        for item in grid.placed:
            self.assertIn(item.entry.clue, page)

    def test_direction_sections(self) -> None:
        grid, numbers = sample_grid()
        page = render_puzzle(grid, numbers)
        self.assertIn("横向", page)
        self.assertIn("纵向", page)

    def test_instruction_present(self) -> None:
        grid, numbers = sample_grid()
        self.assertIn("根据线索", render_puzzle(grid, numbers))

    def test_answers_hidden(self) -> None:
        grid, numbers = sample_grid()
        page = render_puzzle(grid, numbers)
        self.assertNotIn(">CAT<", page)
        self.assertIn('<span class="letter"></span>', page)

    def test_empty_grid_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            render_puzzle(Grid(), {})

    def test_numbers_type_checked(self) -> None:
        grid, _ = sample_grid()
        with self.assertRaises(CrosswordError):
            render_puzzle(grid, [])  # type: ignore[arg-type]

    def test_grid_type_checked(self) -> None:
        with self.assertRaises(CrosswordError):
            render_puzzle("grid", {})  # type: ignore[arg-type]


class TestRenderAnswers(unittest.TestCase):
    def test_answers_visible(self) -> None:
        grid, numbers = sample_grid()
        page = render_answers(grid, numbers)
        for word in grid.placed:
            self.assertIn(word.entry.answer, page)

    def test_word_table(self) -> None:
        grid, numbers = sample_grid()
        page = render_answers(grid, numbers)
        self.assertIn("完整词表", page)
        self.assertIn("<th>编号</th>", page)
        self.assertIn("<th>答案</th>", page)

    def test_answer_title(self) -> None:
        grid, numbers = sample_grid()
        self.assertIn("参考答案", render_answers(grid, numbers))

    def test_answer_clues(self) -> None:
        grid, numbers = sample_grid()
        page = render_answers(grid, numbers)
        self.assertIn("猫咪", page)
        self.assertIn("原子", page)

    def test_empty_grid_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            render_answers(Grid(), {})


class TestRenderDocument(unittest.TestCase):
    def test_two_pages_with_answers(self) -> None:
        grid, numbers = sample_grid()
        page = render_document(grid, numbers, "复习", True)
        self.assertEqual(page.count('<div class="page">'), 2)
        self.assertIn("参考答案", page)

    def test_single_page_without_answers(self) -> None:
        grid, numbers = sample_grid()
        page = render_document(grid, numbers, "复习", False)
        self.assertEqual(page.count('<div class="page">'), 1)
        self.assertNotIn("参考答案", page)

    def test_title_escaped(self) -> None:
        grid, numbers = sample_grid()
        page = render_document(grid, numbers, "<b>标题</b>", True)
        self.assertIn("&lt;b&gt;标题&lt;/b&gt;", page)
        self.assertNotIn("<b>标题</b>", page)

    def test_clue_escaped(self) -> None:
        entries = [
            Entry("CAT", '<script>alert("x")</script>'),
            Entry("ATOM", "原子 & 分子"),
            Entry("OMEN", "征兆"),
            Entry("END", "结束"),
        ]
        grid = build_grid(entries, 9, random.Random(7))
        numbers = number_cells(grid)
        page = render_document(grid, numbers, "安全", True)
        self.assertIn("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;", page)
        self.assertNotIn("<script>alert", page)
        self.assertIn("原子 &amp; 分子", page)

    def test_answer_escaped(self) -> None:
        grid, numbers = sample_grid()
        page = render_document(grid, numbers, "标题", True)
        self.assertIn('<td class="answer">CAT</td>', page)

    def test_non_string_title_raises(self) -> None:
        grid, numbers = sample_grid()
        with self.assertRaises(CrosswordError):
            render_document(grid, numbers, 123, True)  # type: ignore[arg-type]

    def test_empty_grid_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            render_document(Grid(), {}, "标题", True)


if __name__ == "__main__":
    unittest.main()
