"""命令行入口：生成填字游戏 HTML 或示例 CSV。"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path
from typing import List, Optional

from .model import (
    DEFAULT_SIZE,
    MAX_GRID_SIZE,
    MIN_GRID_SIZE,
    CrosswordError,
    Entry,
    build_grid,
    demo_entries,
    number_cells,
    read_csv,
)
from .render import render_document

MAX_TITLE_LENGTH: int = 80


class _ArgumentParser(argparse.ArgumentParser):
    """把 argparse 的英文报错转换成统一的中文异常。"""

    def error(self, message: str) -> None:
        raise CrosswordError(f"参数错误：{message}")


def build_parser() -> argparse.ArgumentParser:
    """构造命令行解析器。

    Returns:
        已注册全部参数的解析器。
    """
    parser = _ArgumentParser(
        prog="crossword",
        description="从「词条,线索」CSV 生成 A4 可打印填字游戏与答案页",
    )
    parser.add_argument("-i", "--input", type=Path, help="词条 CSV 路径（表头 answer,clue）")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("crossword.html"),
        help="输出 HTML 路径（默认 crossword.html）",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=DEFAULT_SIZE,
        help=f"网格尺寸 {MIN_GRID_SIZE}..{MAX_GRID_SIZE}（默认 {DEFAULT_SIZE}）",
    )
    parser.add_argument("--seed", type=int, default=None, help="随机种子，固定后排版可复现")
    parser.add_argument("--no-answers", action="store_true", help="不生成答案页")
    parser.add_argument("--title", default="填字游戏", help="题面标题（默认「填字游戏」）")

    subparsers = parser.add_subparsers(dest="command")
    demo = subparsers.add_parser("demo", help="写出内置示例 CSV")
    demo.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("words.csv"),
        help="示例 CSV 输出路径（默认 words.csv）",
    )
    return parser


def _ensure_parent(path: Path) -> None:
    """确保输出文件的父目录存在。"""
    parent = path.parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)


def _validate_title(title: str) -> str:
    """校验并规范化标题。"""
    if not isinstance(title, str):
        raise CrosswordError("标题必须是文本")
    clean = title.strip()
    if not clean:
        raise CrosswordError("标题不能为空")
    if len(clean) > MAX_TITLE_LENGTH:
        raise CrosswordError(f"标题长度不能超过 {MAX_TITLE_LENGTH} 个字符")
    return clean


def _validate_size(size: int) -> int:
    """校验网格尺寸。"""
    if not isinstance(size, int) or isinstance(size, bool):
        raise CrosswordError("网格尺寸必须是整数")
    if not (MIN_GRID_SIZE <= size <= MAX_GRID_SIZE):
        raise CrosswordError(f"网格尺寸需在 {MIN_GRID_SIZE}..{MAX_GRID_SIZE} 之间")
    return size


def _run_demo(output: Path) -> int:
    """写出内置示例 CSV。"""
    entries = demo_entries()
    _ensure_parent(output)
    try:
        with output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["answer", "clue"])
            for entry in entries:
                writer.writerow([entry.answer, entry.clue])
    except csv.Error as exc:
        raise CrosswordError(f"写入 CSV 失败：{exc}") from exc
    print(f"已生成 {output}（{len(entries)} 个词条）")
    return 0


def _run_generate(
    input_path: Optional[Path],
    output: Path,
    size: int,
    seed: Optional[int],
    title: str,
    show_answers: bool,
) -> int:
    """读取词条、排布网格并写出 HTML。"""
    size = _validate_size(size)
    title = _validate_title(title)

    entries: List[Entry] = read_csv(input_path) if input_path is not None else demo_entries()
    for entry in entries:
        if len(entry.answer) > size:
            raise CrosswordError(
                f"词条「{entry.answer}」长度 {len(entry.answer)} 超过网格尺寸 {size}，请增大 --size"
            )

    rng = random.Random(seed)
    grid = build_grid(entries, size, rng)
    numbers = number_cells(grid)
    document = render_document(grid, numbers, title, show_answers)

    _ensure_parent(output)
    output.write_text(document, encoding="utf-8")
    print(f"已生成 {output}（{len(entries)} 个词条）")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """命令行主函数。

    Args:
        argv: 参数列表；为 None 时读取 sys.argv。

    Returns:
        0 表示成功；1 表示文件不存在或写入失败；2 表示参数/CSV 内容不合法。
    """
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except CrosswordError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    try:
        if args.command == "demo":
            return _run_demo(args.output)
        return _run_generate(
            input_path=args.input,
            output=args.output,
            size=args.size,
            seed=args.seed,
            title=args.title,
            show_answers=not args.no_answers,
        )
    except CrosswordError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        name = exc.filename if exc.filename is not None else "输入文件"
        print(f"错误：找不到文件 {name}", file=sys.stderr)
        return 1
    except IsADirectoryError as exc:
        name = exc.filename if exc.filename is not None else "路径"
        print(f"错误：{name} 是目录，无法写入文件", file=sys.stderr)
        return 1
    except PermissionError as exc:
        name = exc.filename if exc.filename is not None else "路径"
        print(f"错误：没有访问权限 {name}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"错误：文件读写失败（{exc}）", file=sys.stderr)
        return 1
    except UnicodeError as exc:
        print(f"错误：编码处理失败（{exc}）", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
