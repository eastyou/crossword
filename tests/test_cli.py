"""cli 模块单元测试：退出码、文件生成与错误提示。"""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from typing import List, Tuple

from crossword.cli import main
from crossword.model import read_csv

VALID_CSV: str = "answer,clue\nCAT,猫咪\nATOM,原子\nOMEN,征兆\nEND,结束\n"


def run_main(args: List[str]) -> Tuple[int, str, str]:
    """运行 main 并捕获标准输出与标准错误。"""
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(args)
    return code, stdout.getvalue(), stderr.getvalue()


def write_csv(path: Path, text: str) -> None:
    """以 UTF-8 写入 CSV。"""
    path.write_text(text, encoding="utf-8")


class TestDemoCommand(unittest.TestCase):
    def test_demo_writes_csv(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "words.csv"
            code, stdout, stderr = run_main(["demo", "-o", str(output)])
            self.assertEqual(code, 0)
            self.assertEqual(stderr, "")
            self.assertTrue(output.exists())
            self.assertIn("已生成", stdout)

    def test_demo_file_is_readable(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "words.csv"
            run_main(["demo", "-o", str(output)])
            entries = read_csv(output)
            self.assertGreaterEqual(len(entries), 10)
            self.assertEqual(output.read_bytes()[:3], b"\xef\xbb\xbf")

    def test_demo_message_contains_count(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "words.csv"
            _, stdout, _ = run_main(["demo", "-o", str(output)])
            self.assertRegex(stdout, r"已生成 .*（\d+ 个词条）")

    def test_demo_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "nested" / "deep" / "words.csv"
            code, _, _ = run_main(["demo", "-o", str(output)])
            self.assertEqual(code, 0)
            self.assertTrue(output.exists())


class TestGenerateCommand(unittest.TestCase):
    def test_generate_from_csv(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "words.csv"
            output = Path(folder) / "puzzle.html"
            write_csv(source, VALID_CSV)
            code, stdout, stderr = run_main(["-i", str(source), "-o", str(output)])
            self.assertEqual(code, 0)
            self.assertEqual(stderr, "")
            self.assertTrue(output.exists())
            html = output.read_text(encoding="utf-8")
            self.assertIn("<!DOCTYPE html>", html)
            self.assertIn("已生成", stdout)

    def test_generate_message_contains_entry_count(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "words.csv"
            output = Path(folder) / "puzzle.html"
            write_csv(source, VALID_CSV)
            _, stdout, _ = run_main(["-i", str(source), "-o", str(output)])
            self.assertIn("4 个词条", stdout)

    def test_generate_without_input_uses_demo(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "demo.html"
            code, stdout, _ = run_main(["-o", str(output)])
            self.assertEqual(code, 0)
            self.assertTrue(output.exists())
            self.assertIn("12 个词条", stdout)

    def test_no_answers_single_page(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "words.csv"
            output = Path(folder) / "puzzle.html"
            write_csv(source, VALID_CSV)
            code, _, _ = run_main(["-i", str(source), "-o", str(output), "--no-answers"])
            self.assertEqual(code, 0)
            html = output.read_text(encoding="utf-8")
            self.assertEqual(html.count('<div class="page">'), 1)
            self.assertNotIn("参考答案", html)

    def test_seed_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "words.csv"
            first = Path(folder) / "a.html"
            second = Path(folder) / "b.html"
            write_csv(source, VALID_CSV)
            run_main(["-i", str(source), "-o", str(first), "--seed", "7"])
            run_main(["-i", str(source), "-o", str(second), "--seed", "7"])
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_title_in_output(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "words.csv"
            output = Path(folder) / "puzzle.html"
            write_csv(source, VALID_CSV)
            run_main(["-i", str(source), "-o", str(output), "--title", "期末复习"])
            self.assertIn("期末复习", output.read_text(encoding="utf-8"))

    def test_nested_output_directory_created(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "words.csv"
            output = Path(folder) / "a" / "b" / "puzzle.html"
            write_csv(source, VALID_CSV)
            code, _, _ = run_main(["-i", str(source), "-o", str(output)])
            self.assertEqual(code, 0)
            self.assertTrue(output.exists())

    def test_generated_html_is_a4(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "puzzle.html"
            run_main(["-o", str(output), "--seed", "1"])
            html = output.read_text(encoding="utf-8")
            self.assertIn("@page { size: A4; margin: 0 }", html)
            self.assertIn("width: 210mm", html)


class TestCliErrors(unittest.TestCase):
    def test_missing_input_returns_1(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "missing.csv"
            output = Path(folder) / "puzzle.html"
            code, _, stderr = run_main(["-i", str(source), "-o", str(output)])
            self.assertEqual(code, 1)
            self.assertIn("找不到文件", stderr)

    def test_input_directory_returns_1(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "puzzle.html"
            code, _, stderr = run_main(["-i", folder, "-o", str(output)])
            self.assertEqual(code, 1)
            self.assertIn("错误", stderr)

    def test_output_directory_returns_1(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            code, _, stderr = run_main(["-o", folder])
            self.assertEqual(code, 1)
            self.assertIn("错误", stderr)

    def test_size_too_small_returns_2(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            code, _, stderr = run_main(["-o", str(Path(folder) / "a.html"), "--size", "8"])
            self.assertEqual(code, 2)
            self.assertIn("错误", stderr)

    def test_size_too_large_returns_2(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            code, _, stderr = run_main(["-o", str(Path(folder) / "a.html"), "--size", "22"])
            self.assertEqual(code, 2)
            self.assertIn("网格尺寸", stderr)

    def test_non_integer_size_returns_2(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            code, _, stderr = run_main(["-o", str(Path(folder) / "a.html"), "--size", "abc"])
            self.assertEqual(code, 2)
            self.assertIn("参数错误", stderr)

    def test_bad_header_returns_2(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "words.csv"
            output = Path(folder) / "puzzle.html"
            write_csv(source, "answer,question\nCAT,猫\nDOG,狗\nPIG,猪\n")
            code, _, stderr = run_main(["-i", str(source), "-o", str(output)])
            self.assertEqual(code, 2)
            self.assertIn("表头", stderr)

    def test_too_few_entries_returns_2(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "words.csv"
            output = Path(folder) / "puzzle.html"
            write_csv(source, "answer,clue\nCAT,猫\nDOG,狗\n")
            code, _, stderr = run_main(["-i", str(source), "-o", str(output)])
            self.assertEqual(code, 2)
            self.assertIn("至少需要", stderr)

    def test_invalid_answer_returns_2(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "words.csv"
            output = Path(folder) / "puzzle.html"
            write_csv(source, "answer,clue\nC-A-T,猫\nDOG,狗\nPIG,猪\n")
            code, _, stderr = run_main(["-i", str(source), "-o", str(output)])
            self.assertEqual(code, 2)
            self.assertIn("非法字符", stderr)

    def test_answer_longer_than_size_returns_2(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "words.csv"
            output = Path(folder) / "puzzle.html"
            write_csv(source, "answer,clue\nABCDEFGHIJ,十个字符\nDOG,狗\nPIG,猪\n")
            code, _, stderr = run_main(["-i", str(source), "-o", str(output), "--size", "9"])
            self.assertEqual(code, 2)
            self.assertIn("超过网格尺寸", stderr)

    def test_empty_title_returns_2(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            code, _, stderr = run_main(["-o", str(Path(folder) / "a.html"), "--title", "   "])
            self.assertEqual(code, 2)
            self.assertIn("标题不能为空", stderr)

    def test_too_long_title_returns_2(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            code, _, stderr = run_main(
                ["-o", str(Path(folder) / "a.html"), "--title", "长" * 81]
            )
            self.assertEqual(code, 2)
            self.assertIn("标题长度", stderr)

    def test_unknown_option_returns_2(self) -> None:
        code, _, stderr = run_main(["--bogus"])
        self.assertEqual(code, 2)
        self.assertIn("参数错误", stderr)


if __name__ == "__main__":
    unittest.main()
