# crossword

[![CI](https://github.com/eastyou/crossword/actions/workflows/ci.yml/badge.svg)](https://github.com/eastyou/crossword/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)


填字游戏生成器：读入「词条,线索」CSV，自动把词语交叉排进网格，输出 A4 可打印的题面与答案页。
纯 Python 标准库实现，零第三方依赖，适合老师备课、课堂活动与学生作品集。

## 特性

- 词条自动交叉排版，贪心策略尽量多放词
- 支持中文词语按字拆分、英文单词按字母拆分
- A4 打印友好：`@page { size: A4; margin: 0 }`，题面与答案分页
- 每个格子左上角自动编号，横向 / 纵向线索分组展示
- HTML 全量转义，避免线索里的特殊字符破坏页面
- 同 `--seed` 可复现排版结果

## 安装

需要 Python 3.9+。

```bash
pip install -e .
```

也可以不安装，直接在项目根目录运行模块：

```bash
python -m crossword --help
```

## CSV 格式

表头必须包含 `answer` 与 `clue`（大小写不敏感），答案不能含空格与标点，长度 2..10：

```csv
answer,clue
春天,四季之首
天空,头顶上的蓝色世界
空气,看不见却离不开
```

- 空行会被忽略；重复答案只保留第一条
- 有效词条至少 3 条
- 支持 `utf-8-sig`（带 BOM 的 Excel 导出）与 `gbk` 编码自动回退

示例文件见 [`examples/words.csv`](examples/words.csv)。

## 使用

生成内置示例 CSV：

```bash
python -m crossword demo -o examples/words.csv
```

从 CSV 生成题面与答案：

```bash
python -m crossword -i examples/words.csv -o examples/crossword.html --size 13 --seed 2026
```

不传 `-i` 时直接使用内置示例词条：

```bash
python -m crossword -o crossword.html
```

常用参数：

| 参数 | 说明 |
| --- | --- |
| `-i, --input` | 词条 CSV 路径 |
| `-o, --output` | 输出 HTML 路径，默认 `crossword.html` |
| `--size` | 网格尺寸 9..21，默认 13 |
| `--seed` | 随机种子，固定后排版可复现 |
| `--no-answers` | 只输出题面，不附答案页 |
| `--title` | 题面标题，默认「填字游戏」 |

生成成功会打印「已生成 <path>（N 个词条）」。

## 退出码

| 退出码 | 含义 |
| --- | --- |
| 0 | 成功 |
| 1 | 文件不存在或写入失败 |
| 2 | 参数或 CSV 内容不合法（错误信息输出到 stderr） |

## 测试

```bash
python -m unittest discover -s tests -v
```

## 目录结构

```
crossword/
├── crossword/
│   ├── __init__.py
│   ├── __main__.py
│   ├── model.py      # 校验、CSV、网格排布、编号
│   ├── render.py     # A4 HTML 渲染
│   └── cli.py        # 命令行入口
├── tests/
├── examples/
└── pyproject.toml
```

## 许可证

MIT © 2026 eastyou
