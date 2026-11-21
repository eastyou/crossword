"""model 模块单元测试：校验、CSV、排布与编号。"""

from __future__ import annotations

import math
import random
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Dict, List, Set, Tuple

from crossword.model import (
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


def ascii_entries() -> List[Entry]:
    """构造一组可交叉的英文词条，便于断言。"""
    return [
        Entry("CAT", "猫咪"),
        Entry("ATOM", "原子"),
        Entry("OMEN", "征兆"),
        Entry("END", "结束"),
    ]


def occupied_cells(placed: Placed) -> List[Tuple[int, int]]:
    """按答案字符顺序计算一条已放置词条占用的坐标。"""
    if placed.direction == "across":
        return [(placed.row, placed.col + offset) for offset in range(len(placed.entry.answer))]
    return [(placed.row + offset, placed.col) for offset in range(len(placed.entry.answer))]


class TestNormalizeAnswer(unittest.TestCase):
    def test_upper_ascii(self) -> None:
        self.assertEqual(normalize_answer("cat"), "CAT")

    def test_strip_outer_spaces(self) -> None:
        self.assertEqual(normalize_answer("  春天  "), "春天")

    def test_strip_newline(self) -> None:
        self.assertEqual(normalize_answer("cat\n"), "CAT")

    def test_empty_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            normalize_answer("")

    def test_only_spaces_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            normalize_answer("   ")

    def test_non_string_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            normalize_answer(123)  # type: ignore[arg-type]

    def test_inner_space_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            normalize_answer("春 天")

    def test_fullwidth_space_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            normalize_answer("春　天")

    def test_punctuation_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            normalize_answer("C-A-T")

    def test_chinese_punctuation_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            normalize_answer("春天，")

    def test_too_short_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            normalize_answer("A")

    def test_too_long_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            normalize_answer("ABCDEFGHIJK")

    def test_min_length_accepted(self) -> None:
        self.assertEqual(normalize_answer("ab"), "AB")

    def test_max_length_accepted(self) -> None:
        self.assertEqual(normalize_answer("abcdefghij"), "ABCDEFGHIJ")

    def test_chinese_accepted(self) -> None:
        self.assertEqual(normalize_answer("秋天"), "秋天")


class TestEntryModel(unittest.TestCase):
    def test_entry_is_frozen(self) -> None:
        entry = Entry("CAT", "猫咪")
        with self.assertRaises(FrozenInstanceError):
            entry.answer = "DOG"  # type: ignore[misc]

    def test_entry_equality(self) -> None:
        self.assertEqual(Entry("CAT", "猫咪"), Entry("CAT", "猫咪"))


class TestParseCsvText(unittest.TestCase):
    def test_parse_basic(self) -> None:
        text = "answer,clue\ncat, 猫咪 \ndog,小狗\npig,猪\n"
        entries = parse_csv_text(text)
        self.assertEqual([item.answer for item in entries], ["CAT", "DOG", "PIG"])
        self.assertEqual(entries[0].clue, "猫咪")

    def test_header_case_and_spaces(self) -> None:
        text = " Answer , Clue \nCAT,猫\nDOG,狗\nPIG,猪\n"
        self.assertEqual(len(parse_csv_text(text)), 3)

    def test_bom_in_text(self) -> None:
        text = "\ufeffanswer,clue\nCAT,猫\nDOG,狗\nPIG,猪\n"
        self.assertEqual(len(parse_csv_text(text)), 3)

    def test_missing_clue_header_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            parse_csv_text("answer,question\nCAT,猫\nDOG,狗\nPIG,猪\n")

    def test_missing_answer_header_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            parse_csv_text("question,clue\n猫,猫\n狗,狗\n猪,猪\n")

    def test_empty_text_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            parse_csv_text("")

    def test_whitespace_only_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            parse_csv_text("  \n ")

    def test_non_string_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            parse_csv_text(123)  # type: ignore[arg-type]

    def test_empty_answer_raises(self) -> None:
        text = "answer,clue\n,猫\nDOG,狗\nPIG,猪\n"
        with self.assertRaises(CrosswordError):
            parse_csv_text(text)

    def test_empty_clue_raises(self) -> None:
        text = "answer,clue\nCAT,猫\nDOG,\nPIG,猪\n"
        with self.assertRaises(CrosswordError):
            parse_csv_text(text)

    def test_duplicate_keeps_first(self) -> None:
        text = "answer,clue\ncat,第一次\nCAT,第二次\nDOG,狗\nPIG,猪\n"
        entries = parse_csv_text(text)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0].clue, "第一次")

    def test_duplicates_below_three_raises(self) -> None:
        text = "answer,clue\nCAT,猫\nCAT,猫\nDOG,狗\n"
        with self.assertRaises(CrosswordError):
            parse_csv_text(text)

    def test_short_row_raises(self) -> None:
        text = "answer,clue\nCAT,猫\nDOG\nPIG,猪\n"
        with self.assertRaises(CrosswordError):
            parse_csv_text(text)

    def test_blank_lines_ignored(self) -> None:
        text = "\nanswer,clue\n\nCAT,猫\n\nDOG,狗\nPIG,猪\n\n"
        self.assertEqual(len(parse_csv_text(text)), 3)

    def test_quoted_comma_in_clue(self) -> None:
        text = 'answer,clue\nCAT,"会,叫"\nDOG,狗\nPIG,猪\n'
        self.assertEqual(parse_csv_text(text)[0].clue, "会,叫")

    def test_extra_columns_ignored(self) -> None:
        text = "answer,clue,note\nCAT,猫,备注\nDOG,狗,备注\nPIG,猪,备注\n"
        self.assertEqual(len(parse_csv_text(text)), 3)

    def test_reordered_columns(self) -> None:
        text = "clue,answer\n猫,CAT\n狗,DOG\n猪,PIG\n"
        entries = parse_csv_text(text)
        self.assertEqual([item.answer for item in entries], ["CAT", "DOG", "PIG"])

    def test_invalid_answer_in_csv_raises(self) -> None:
        text = "answer,clue\nC-A-T,猫\nDOG,狗\nPIG,猪\n"
        with self.assertRaises(CrosswordError):
            parse_csv_text(text)

    def test_header_only_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            parse_csv_text("answer,clue\n")


class TestReadCsv(unittest.TestCase):
    CSV_TEXT: str = "answer,clue\nCAT,猫\nDOG,狗\nPIG,猪\n"

    def test_read_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "words.csv"
            path.write_text(self.CSV_TEXT, encoding="utf-8")
            entries = read_csv(path)
            self.assertEqual(len(entries), 3)
            self.assertEqual(entries[0].answer, "CAT")

    def test_read_utf8_sig(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "words.csv"
            path.write_text(self.CSV_TEXT, encoding="utf-8-sig")
            self.assertEqual(len(read_csv(path)), 3)

    def test_read_gbk(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "words.csv"
            path.write_bytes(self.CSV_TEXT.encode("gbk"))
            entries = read_csv(path)
            self.assertEqual(entries[0].clue, "猫")

    def test_missing_file_raises(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "missing.csv"
            with self.assertRaises(FileNotFoundError):
                read_csv(path)

    def test_undecodable_raises(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "broken.csv"
            path.write_bytes(b"\xff\xff\xff\xff")
            with self.assertRaises(CrosswordError):
                read_csv(path)

    def test_string_path_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "words.csv"
            path.write_text(self.CSV_TEXT, encoding="utf-8")
            entries = read_csv(str(path))  # type: ignore[arg-type]
            self.assertEqual(len(entries), 3)


class TestIsValidPosition(unittest.TestCase):
    def test_valid_on_empty_grid(self) -> None:
        self.assertTrue(is_valid_position({}, "CAT", 2, 2, "across", 9))

    def test_conflict_letter_rejected(self) -> None:
        cells: Dict[Tuple[int, int], str] = {(2, 2): "D"}
        self.assertFalse(is_valid_position(cells, "CAT", 2, 2, "across", 9))

    def test_out_of_bounds_rejected(self) -> None:
        self.assertFalse(is_valid_position({}, "CAT", 2, 7, "across", 9))
        self.assertFalse(is_valid_position({}, "CAT", -1, 0, "across", 9))

    def test_extend_existing_word_rejected(self) -> None:
        cells = {(2, 2): "C", (2, 3): "A", (2, 4): "T"}
        self.assertFalse(is_valid_position(cells, "CAT", 2, 1, "across", 9))

    def test_adjacent_parallel_word_rejected(self) -> None:
        cells = {(3, 2): "D", (3, 3): "O", (3, 4): "G"}
        self.assertFalse(is_valid_position(cells, "CAT", 2, 2, "across", 9))

    def test_crossing_allowed(self) -> None:
        cells = {(2, 2): "C", (3, 2): "A", (4, 2): "T"}
        self.assertTrue(is_valid_position(cells, "ATOM", 3, 2, "across", 9))

    def test_invalid_direction_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            is_valid_position({}, "CAT", 0, 0, "diagonal", 9)

    def test_empty_answer_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            is_valid_position({}, "", 0, 0, "across", 9)

    def test_invalid_size_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            is_valid_position({}, "CAT", 0, 0, "across", 0)

    def test_invalid_cells_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            is_valid_position([], "CAT", 0, 0, "across", 9)  # type: ignore[arg-type]

    def test_invalid_coordinate_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            is_valid_position({}, "CAT", 0.5, 0, "across", 9)  # type: ignore[arg-type]


class TestBuildGrid(unittest.TestCase):
    def test_first_entry_placed_across(self) -> None:
        entries = ascii_entries()
        grid = build_grid(entries, 9, random.Random(1))
        self.assertEqual(grid.placed[0].entry, entries[0])
        self.assertEqual(grid.placed[0].direction, "across")

    def test_all_ascii_entries_placed(self) -> None:
        grid = build_grid(ascii_entries(), 9, random.Random(2))
        self.assertEqual(len(grid.placed), len(ascii_entries()))

    def test_letters_match_cells(self) -> None:
        grid = build_grid(ascii_entries(), 9, random.Random(3))
        for word in grid.placed:
            for (row, col), char in zip(occupied_cells(word), word.entry.answer):
                self.assertEqual(grid.cells[(row, col)], char)

    def test_every_later_word_crosses(self) -> None:
        grid = build_grid(ascii_entries(), 9, random.Random(4))
        covered: Set[Tuple[int, int]] = set()
        for index, word in enumerate(grid.placed):
            cells = set(occupied_cells(word))
            if index > 0:
                self.assertTrue(cells & covered)
            covered |= cells

    def test_demo_ratio_at_least_60_percent(self) -> None:
        entries = demo_entries()
        grid = build_grid(entries, 13, random.Random(5))
        self.assertGreaterEqual(len(grid.placed), math.ceil(len(entries) * 0.6))

    def test_demo_has_at_least_ten_entries(self) -> None:
        self.assertGreaterEqual(len(demo_entries()), 10)

    def test_reproducible_with_same_seed(self) -> None:
        first = build_grid(demo_entries(), 13, random.Random(2026))
        second = build_grid(demo_entries(), 13, random.Random(2026))
        self.assertEqual(grid_preview(first), grid_preview(second))
        self.assertEqual(
            [item.entry.answer for item in first.placed],
            [item.entry.answer for item in second.placed],
        )

    def test_grid_trimmed_to_used_area(self) -> None:
        grid = build_grid(ascii_entries(), 9, random.Random(6))
        rows = [row for row, _ in grid.cells]
        cols = [col for _, col in grid.cells]
        self.assertEqual(min(rows), 0)
        self.assertEqual(min(cols), 0)
        self.assertEqual(max(rows), grid.height - 1)
        self.assertEqual(max(cols), grid.width - 1)

    def test_preview_dimensions(self) -> None:
        grid = build_grid(ascii_entries(), 9, random.Random(7))
        preview = grid_preview(grid)
        self.assertEqual(len(preview), grid.height)
        for line in preview:
            self.assertEqual(len(line), grid.width)

    def test_too_few_entries_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            build_grid([Entry("CAT", "猫"), Entry("DOG", "狗")], 9, random.Random(1))

    def test_size_too_small_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            build_grid(ascii_entries(), 8, random.Random(1))

    def test_size_too_large_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            build_grid(ascii_entries(), 22, random.Random(1))

    def test_first_answer_longer_than_size_raises(self) -> None:
        entries = [Entry("ABCDEFGHIJ", "太长"), Entry("CAT", "猫"), Entry("DOG", "狗")]
        with self.assertRaises(CrosswordError):
            build_grid(entries, 9, random.Random(1))

    def test_disconnected_entries_raise(self) -> None:
        entries = [Entry("CAT", "猫"), Entry("DOG", "狗"), Entry("PIG", "猪")]
        with self.assertRaises(CrosswordError):
            build_grid(entries, 9, random.Random(1))

    def test_invalid_rng_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            build_grid(ascii_entries(), 9, "seed")  # type: ignore[arg-type]

    def test_non_list_entries_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            build_grid("CAT", 9, random.Random(1))  # type: ignore[arg-type]

    def test_preview_rejects_non_grid(self) -> None:
        with self.assertRaises(CrosswordError):
            grid_preview({"a": 1})  # type: ignore[arg-type]


class TestNumberCells(unittest.TestCase):
    def test_numbers_are_continuous(self) -> None:
        grid = build_grid(ascii_entries(), 9, random.Random(8))
        numbers = number_cells(grid)
        self.assertEqual(sorted(numbers.values()), list(range(1, len(numbers) + 1)))

    def test_only_word_starts_numbered(self) -> None:
        grid = build_grid(ascii_entries(), 9, random.Random(9))
        numbers = number_cells(grid)
        starts = {(item.row, item.col) for item in grid.placed}
        self.assertEqual(set(numbers), starts)

    def test_shared_start_gets_single_number(self) -> None:
        grid = Grid(
            cells={(0, 0): "A", (0, 1): "B", (1, 0): "C"},
            placed=[Placed(Entry("AB", "横"), 0, 0, "across"), Placed(Entry("AC", "纵"), 0, 0, "down")],
            width=2,
            height=2,
        )
        self.assertEqual(number_cells(grid), {(0, 0): 1})

    def test_scan_order_follows_rows(self) -> None:
        grid = Grid(
            cells={(0, 0): "A", (0, 1): "B", (1, 1): "D"},
            placed=[Placed(Entry("AB", "横"), 0, 0, "across"), Placed(Entry("BD", "纵"), 0, 1, "down")],
            width=2,
            height=2,
        )
        self.assertEqual(number_cells(grid), {(0, 0): 1, (0, 1): 2})

    def test_empty_grid_has_no_numbers(self) -> None:
        self.assertEqual(number_cells(Grid()), {})

    def test_non_grid_raises(self) -> None:
        with self.assertRaises(CrosswordError):
            number_cells("grid")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
