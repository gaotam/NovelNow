# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

NovelNow là Python CLI scrape chương mới của truyện từ nhiều site Việt (truyện chữ + truyện tranh) rồi gửi thông báo vào
Discord. State của user (danh sách truyện + chương mới nhất đã thấy) sống trong `data.json` ở repo root — file này vừa
là input vừa là output mỗi lần chạy.

## Commands

```bash
# Setup (Python >= 3.11, dùng tomllib stdlib)
pip install -r requirements.txt
cp config.example.toml config.toml   # rồi điền bot_token + general_channel_id

# Run
python main.py

# Tests (chạy unittest, các provider test CHẠM endpoint thật → cần mạng + config.toml)
python -m unittest discover -s tests
python -m unittest tests.test_goctruyentranhvui_provider
python -m unittest tests.test_goctruyentranhvui_provider.TestGocTruyenTranhVuiProvider.test_fetches_latest_chapter_when_data_is_valid
```

Note: `config.toml` đã có giá trị thật (bot token + cf_clearance) — KHÔNG commit thay đổi vào file này, KHÔNG paste
content ra log/PR.

## Architecture

Một-shot pipeline trong `Runner.run()` (`runner/__init__.py`):

```
load_config_project() → load data.json → Story(**d) cho mỗi entry
  → fetch_latest_chapters() (loop tuần tự, sleep story_fetch_delay_sec)
  → log_output_console + input("y/N") xác nhận
  → send_general_channel (chunked) + send_story_channels
  → update_data() ghi lại data.json (lọc bỏ truyện completed, sort theo update_date)
```

### Provider plug-in pattern

`providers/base.py:BaseProvider` (ABC) định nghĩa contract:

- `get_story_info() -> StoryInfo` (latest_chapter, latest_chapter_date, status)
- `get_link_chapter(chapter: int) -> str`

Mỗi site impl một subclass và self-register qua `providers/__init__.py:PROVIDER_MAP`, keyed bởi `consts.ProviderName`
enum value. `Story.__post_init__` resolve `source` string → provider class. **Thêm provider mới**: tạo file trong
`providers/`, set `self.name = "..."`, thêm vào `ProviderName` enum + `PROVIDER_MAP` + `ENDPOINTS` (
`consts/enpoint.py`).

Provider tự đọc config riêng qua `get_config(f"provider.{self.name}")` — ví dụ `goctruyentranhvui` cần `user_agent` +
`cf_clearance` để qua Cloudflare.

### Story state machine

`runner/story.py:Story` là dataclass + state cho mỗi truyện. Field `error: StoryError` (enum trong `consts/errors.py`)
persist trong `data.json` để retry partial-failure ở run sau — phân biệt lỗi gửi general channel vs gửi story channel.
Helper `resolve_or_set_error(success, error_type)` flip state dựa vào kết quả send.

`source == "metruyenchu"` được skip ở `Story.get_latest_chapter` (logic riêng chưa impl) và đánh dấu là "truyện chữ" ở
console output.

### Config

`utils/config.py` là singleton TOML loader. Phải gọi `load_config_project()` trước khi gọi `get_config("section.key")` —
nếu không sẽ raise `RuntimeError`. Test cũng phải gọi `load_config_project()` ở setup.

### Logging

`logger.py:setup_logger()` trả về singleton logger (idempotent qua `hasHandlers()` check). File log: `logs/app.log` (
DEBUG, append, UTF-8). Console: INFO+, có ANSI color. `PrefixAdapter` được Runner inject vào mỗi Story để log có prefix
`[idx/total]`.

## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool                        | Use when                                               |
|-----------------------------|--------------------------------------------------------|
| `detect_changes`            | Reviewing code changes - gives risk-scored analysis    |
| `get_review_context`        | Need source snippets for review - token-efficient      |
| `get_impact_radius`         | Understanding blast radius of a change                 |
| `get_affected_flows`        | Finding which execution paths are impacted             |
| `query_graph`               | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes`     | Finding functions/classes by name or keyword           |
| `get_architecture_overview` | Understanding high-level codebase structure            |
| `refactor_tool`             | Planning renames, finding dead code                    |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.
