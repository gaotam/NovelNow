# NovelNow

## 1. Cài dependencies
```bash
pip install -r requirements.txt
```

## 2. Cấu hình
1. Tạo `config.toml` từ `config.example.toml`.
2. Điền các giá trị cần thiết (ví dụ: `discord.bot_token`, `discord.general_channel_id`).
3. Thêm/sửa danh sách truyện trong `data.json`.

## 3. Chạy app
```bash
python main.py
```

## Tracking (SQLite)
- Source-of-truth của danh sách truyện hiện là SQLite trong `story_tracking.db` (bảng `stories`).
- Lần chạy đầu, nếu DB chưa có dữ liệu, app sẽ bootstrap từ `data.json`.
- `data.json` không còn là nơi đọc chính; file này chỉ được đồng bộ ngược từ SQLite mỗi `3` ngày.
- Tracking chapter hiện dùng SQLite: `story_tracking.db`.
- Bảng: `story_snapshots`.
- Unique theo `(channel_id, snapshot_date)` nên không bị trùng snapshot cùng ngày.
- Giới hạn tối đa `30` snapshot mới nhất cho mỗi `channel_id`.
- File `story_tracking.json` đã ngừng dùng.
- Backup JSON cũ (nếu có): `story_tracking.backup_*.json`.
