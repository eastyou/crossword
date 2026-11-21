"""填字游戏核心模型：词条校验、CSV 解析、网格排布与编号。"""

from __future__ import annotations

import csv
import io
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

MIN_ANSWER_LENGTH: int = 2
MAX_ANSWER_LENGTH: int = 10
MIN_ENTRIES: int = 3
MIN_GRID_SIZE: int = 9
MAX_GRID_SIZE: int = 21
REQUIRED_PLACEMENT_RATIO: float = 0.6
DEFAULT_SIZE: int = 13

Cell = Tuple[int, int]
Direction = str

DIRECTIONS: Tuple[str, str] = ("across", "down")


class CrosswordError(ValueError):
    """填字游戏自定义异常：输入数据或参数不合法时抛出。"""


@dataclass(frozen=True)
class Entry:
    """一条待排布的填字词条。"""

    answer: str
    clue: str


@dataclass
class Placed:
    """已放置到网格中的词条。"""

    entry: Entry
    row: int
    col: int
    direction: Direction  # "across" | "down"


@dataclass
class Grid:
    """排布结果：格子内容、词条位置与网格尺寸。"""

    cells: Dict[Cell, str] = field(default_factory=dict)
    placed: List[Placed] = field(default_factory=list)
    width: int = 0
    height: int = 0


def normalize_answer(raw: str) -> str:
    """校验并规范化答案：去除首尾空白、英文转大写。

    答案必须为 2..10 个字符，字符只能是字母或数字（支持中文），
    不能包含内部空格或标点。

    Args:
        raw: 原始答案文本。

    Returns:
        规范化后的答案。

    Raises:
        CrosswordError: 答案非文本、为空、含空格/标点或长度不符时抛出。
    """
    if not isinstance(raw, str):
        raise CrosswordError("答案必须是文本")
    core = raw.strip()
    if not core:
        raise CrosswordError("答案不能为空")
    if any(ch.isspace() for ch in core):
        raise CrosswordError(f"答案「{raw}」不能包含空格")
    core = core.upper()
    length = len(core)
    if length < MIN_ANSWER_LENGTH or length > MAX_ANSWER_LENGTH:
        raise CrosswordError(
            f"答案「{core}」长度为 {length}，需在 {MIN_ANSWER_LENGTH}..{MAX_ANSWER_LENGTH} 之间"
        )
    invalid = sorted({ch for ch in core if not ch.isalnum()})
    if invalid:
        joined = "、".join(invalid)
        raise CrosswordError(f"答案「{core}」含非法字符：{joined}")
    return core


def parse_csv_text(text: str) -> List[Entry]:
    """解析 CSV 文本并校验词条。

    表头必须包含 answer 与 clue（大小写不敏感）。逐行校验答案与线索，
    重复答案只保留第一条，去重后至少需要 3 条有效词条。

    Args:
        text: CSV 全文。

    Returns:
        按出现顺序排列的词条列表。

    Raises:
        CrosswordError: 文本非字符串、表头缺失、字段缺失、答案非法或词条不足时抛出。
    """
    if not isinstance(text, str):
        raise CrosswordError("CSV 内容必须是文本")
    clean = text.lstrip("\ufeff")
    reader = csv.reader(io.StringIO(clean))
    try:
        rows = [row for row in reader]
    except csv.Error as exc:
        raise CrosswordError(f"CSV 解析失败：{exc}") from exc

    header_index: Optional[int] = None
    for index, row in enumerate(rows):
        if any(cell.strip() for cell in row):
            header_index = index
            break
    if header_index is None:
        raise CrosswordError("CSV 内容为空，需要表头 answer,clue")

    header = [cell.strip().lower() for cell in rows[header_index]]
    if "answer" not in header or "clue" not in header:
        raise CrosswordError("CSV 表头必须包含 answer 与 clue")
    answer_index = header.index("answer")
    clue_index = header.index("clue")
    needed = max(answer_index, clue_index)

    entries: List[Entry] = []
    seen: Dict[str, bool] = {}
    for offset, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) <= needed:
            raise CrosswordError(f"第 {offset} 行字段不足，需要包含 answer 与 clue")
        answer = normalize_answer(row[answer_index])
        clue = row[clue_index].strip()
        if not clue:
            raise CrosswordError(f"第 {offset} 行线索不能为空")
        if answer in seen:
            continue
        seen[answer] = True
        entries.append(Entry(answer=answer, clue=clue))

    if len(entries) < MIN_ENTRIES:
        raise CrosswordError(
            f"有效词条只有 {len(entries)} 条，至少需要 {MIN_ENTRIES} 条（去重后）"
        )
    return entries


def read_csv(path: Path) -> List[Entry]:
    """读取 CSV 文件，按 utf-8-sig、gbk 顺序尝试解码。

    Args:
        path: CSV 文件路径。

    Returns:
        校验后的词条列表。

    Raises:
        FileNotFoundError: 文件不存在时抛出，由 CLI 映射为退出码 1。
        CrosswordError: 两种编码都无法解码或内容非法时抛出。
    """
    if not isinstance(path, Path):
        try:
            path = Path(path)
        except TypeError as exc:
            raise CrosswordError("CSV 路径不合法") from exc
    data = path.read_bytes()
    last_error: Optional[UnicodeDecodeError] = None
    for encoding in ("utf-8-sig", "gbk"):
        try:
            decoded = data.decode(encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
        return parse_csv_text(decoded)
    raise CrosswordError(f"无法识别 CSV 编码（已尝试 utf-8-sig 与 gbk）：{path.name}") from last_error


def demo_entries() -> List[Entry]:
    """返回内置示例词条（中文词语及其线索）。

    Returns:
        至少 10 条可互相交叉的示例词条。
    """
    pairs: Sequence[Tuple[str, str]] = (
        ("春天", "四季之首"),
        ("天空", "头顶上的蓝色世界"),
        ("空气", "看不见却离不开"),
        ("气球", "吹大后会升空的玩具"),
        ("球拍", "打球时握在手里的工具"),
        ("拍手", "表示欢迎或赞赏的动作"),
        ("手指", "手掌上的五个小伙伴"),
        ("指南", "辨别方向的工具"),
        ("南方", "天气通常较热的方位"),
        ("方向", "东南西北所指"),
        ("向上", "朝着高处"),
        ("上学", "每天背起书包去做的事"),
    )
    return [Entry(answer=normalize_answer(answer), clue=clue) for answer, clue in pairs]


def _cells_for(answer: str, row: int, col: int, direction: Direction) -> List[Cell]:
    """计算从 (row, col) 开始沿某方向放置 answer 所占的格子坐标。"""
    if direction == "across":
        return [(row, col + offset) for offset in range(len(answer))]
    if direction == "down":
        return [(row + offset, col) for offset in range(len(answer))]
    raise CrosswordError(f"未知方向：{direction}")


def is_valid_position(
    cells: Dict[Cell, str],
    answer: str,
    row: int,
    col: int,
    direction: Direction,
    size: int,
) -> bool:
    """判断词条能否放在指定位置。

    规则：不越界、同格字符一致、词首尾外侧无多余字母、
    新格子的垂直相邻格必须为空（避免生成未声明的词）。

    Args:
        cells: 当前已占用格子及其字符。
        answer: 待放置的规范化答案。
        row: 起始行。
        col: 起始列。
        direction: "across" 或 "down"。
        size: 正方形网格边长。

    Returns:
        可以放置返回 True，否则返回 False。

    Raises:
        CrosswordError: 参数类型或取值不合法时抛出。
    """
    if not isinstance(cells, dict):
        raise CrosswordError("cells 必须是字典")
    if not isinstance(answer, str) or not answer:
        raise CrosswordError("待放置的答案不能为空")
    if not isinstance(row, int) or not isinstance(col, int):
        raise CrosswordError("起始坐标必须是整数")
    if direction not in DIRECTIONS:
        raise CrosswordError(f"未知方向：{direction}")
    if not isinstance(size, int) or size < 1:
        raise CrosswordError("网格尺寸必须是正整数")

    coords = _cells_for(answer, row, col, direction)
    if any(r < 0 or c < 0 or r >= size or c >= size for r, c in coords):
        return False

    if direction == "across":
        before: Cell = (row, col - 1)
        after: Cell = (row, col + len(answer))
        perpendicular_offsets = ((-1, 0), (1, 0))
    else:
        before = (row - 1, col)
        after = (row + len(answer), col)
        perpendicular_offsets = ((0, -1), (0, 1))

    if before in cells or after in cells:
        return False

    for (r, c), char in zip(coords, answer):
        existing = cells.get((r, c))
        if existing is not None:
            if existing != char:
                return False
            continue
        for dr, dc in perpendicular_offsets:
            if (r + dr, c + dc) in cells:
                return False
    return True


def _find_placement(
    cells: Dict[Cell, str],
    placed: List[Placed],
    entry: Entry,
    size: int,
    rng: random.Random,
) -> Optional[Tuple[int, int, Direction]]:
    """为词条寻找与已放词交叉且冲突最少（优先多次交叉）的位置。"""
    candidates: List[Tuple[int, int, Direction, int]] = []
    seen: Dict[Tuple[int, int, Direction], bool] = {}
    for word in placed:
        for index, char in enumerate(word.entry.answer):
            if char not in entry.answer:
                continue
            if word.direction == "across":
                crossing: Cell = (word.row, word.col + index)
                direction: Direction = "down"
            else:
                crossing = (word.row + index, word.col)
                direction = "across"
            for answer_index, own_char in enumerate(entry.answer):
                if own_char != char:
                    continue
                if direction == "down":
                    row = crossing[0] - answer_index
                    col = crossing[1]
                else:
                    row = crossing[0]
                    col = crossing[1] - answer_index
                key = (row, col, direction)
                if key in seen:
                    continue
                if not is_valid_position(cells, entry.answer, row, col, direction, size):
                    continue
                seen[key] = True
                coords = _cells_for(entry.answer, row, col, direction)
                crossings = sum(1 for coord in coords if coord in cells)
                candidates.append((row, col, direction, crossings))
    if not candidates:
        return None
    rng.shuffle(candidates)
    best = max(candidates, key=lambda item: item[3])
    return best[0], best[1], best[2]


def _attempt_build(entries: List[Entry], size: int, rng: random.Random) -> Grid:
    """完成一次贪心排布尝试，返回裁剪后的网格。"""
    cells: Dict[Cell, str] = {}
    placed: List[Placed] = []

    first = entries[0]
    start_row = size // 2
    start_col = max(0, min((size - len(first.answer)) // 2, size - len(first.answer)))
    for offset, char in enumerate(first.answer):
        cells[(start_row, start_col + offset)] = char
    placed.append(Placed(entry=first, row=start_row, col=start_col, direction="across"))

    pending: List[Entry] = list(entries[1:])
    rng.shuffle(pending)
    while pending:
        failed: List[Entry] = []
        for entry in pending:
            if len(entry.answer) > size:
                failed.append(entry)
                continue
            placement = _find_placement(cells, placed, entry, size, rng)
            if placement is None:
                failed.append(entry)
                continue
            row, col, direction = placement
            for (r, c), char in zip(_cells_for(entry.answer, row, col, direction), entry.answer):
                cells[(r, c)] = char
            placed.append(Placed(entry=entry, row=row, col=col, direction=direction))
        if len(failed) == len(pending):
            break
        pending = failed

    rows = [r for r, _ in cells]
    cols = [c for _, c in cells]
    min_row, max_row = min(rows), max(rows)
    min_col, max_col = min(cols), max(cols)
    trimmed_cells = {
        (r - min_row, c - min_col): char for (r, c), char in cells.items()
    }
    trimmed_placed = [
        Placed(
            entry=item.entry,
            row=item.row - min_row,
            col=item.col - min_col,
            direction=item.direction,
        )
        for item in placed
    ]
    return Grid(
        cells=trimmed_cells,
        placed=trimmed_placed,
        width=max_col - min_col + 1,
        height=max_row - min_row + 1,
    )


def build_grid(entries: List[Entry], size: int, rng: random.Random) -> Grid:
    """用贪心策略把词条交叉排进网格。

    第一条词横放并居中，后续词条寻找与已放词共享字符的交叉点。
    会按不同顺序多次尝试，取放置词条最多的一次；放不下的词跳过。
    放置率不足 60% 时抛错。最终裁剪到实际使用范围。

    Args:
        entries: 已校验的词条列表。
        size: 正方形网格边长（9..21）。
        rng: 随机数发生器，决定候选位置与放置顺序，便于复现。

    Returns:
        裁剪后的网格。

    Raises:
        CrosswordError: 词条不足、尺寸非法、首词超长或放置率不足时抛出。
    """
    if not isinstance(entries, (list, tuple)):
        raise CrosswordError("词条必须是列表")
    if len(entries) < MIN_ENTRIES:
        raise CrosswordError(f"至少需要 {MIN_ENTRIES} 条词条才能生成填字游戏")
    if not isinstance(size, int) or not (MIN_GRID_SIZE <= size <= MAX_GRID_SIZE):
        raise CrosswordError(f"网格尺寸需在 {MIN_GRID_SIZE}..{MAX_GRID_SIZE} 之间")
    if not isinstance(rng, random.Random):
        raise CrosswordError("随机数发生器不合法")

    first = entries[0]
    if len(first.answer) > size:
        raise CrosswordError(f"词条「{first.answer}」长度超过网格尺寸 {size}，请增大 --size")

    required = math.ceil(len(entries) * REQUIRED_PLACEMENT_RATIO)
    best: Optional[Grid] = None
    best_count = 0
    for _ in range(8):
        candidate = _attempt_build(entries, size, rng)
        if len(candidate.placed) > best_count:
            best = candidate
            best_count = len(candidate.placed)
        if best_count == len(entries):
            break

    if best is None or best_count < required:
        raise CrosswordError(
            f"仅放置 {best_count}/{len(entries)} 条词条，未达到 60%，"
            "请增加 --size 或提供更多可交叉的词条"
        )
    return best


def number_cells(grid: Grid) -> Dict[Cell, int]:
    """按行列扫描，为横向或纵向词的起点依次编号。

    Args:
        grid: 已排布的网格。

    Returns:
        起点坐标到编号（从 1 开始）的映射。

    Raises:
        CrosswordError: 参数不是 Grid 时抛出。
    """
    if not isinstance(grid, Grid):
        raise CrosswordError("grid 参数必须是 Grid 实例")
    starts = {(item.row, item.col) for item in grid.placed}
    numbers: Dict[Cell, int] = {}
    counter = 1
    for row in range(grid.height):
        for col in range(grid.width):
            cell = (row, col)
            if cell in starts:
                numbers[cell] = counter
                counter += 1
    return numbers


def grid_preview(grid: Grid) -> List[str]:
    """生成用于调试与测试的字符预览，空格用 '.' 表示。

    Args:
        grid: 已排布的网格。

    Returns:
        每行一个字符串的列表。

    Raises:
        CrosswordError: 参数不是 Grid 时抛出。
    """
    if not isinstance(grid, Grid):
        raise CrosswordError("grid 参数必须是 Grid 实例")
    lines: List[str] = []
    for row in range(grid.height):
        lines.append(
            "".join(grid.cells.get((row, col), ".") for col in range(grid.width))
        )
    return lines
