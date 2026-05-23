# NovelNow Local-First Refactor Plan

## Mục tiêu
- Giữ nguyên HTTP layer hiện tại.
- Giữ nguyên logic gửi Discord hiện tại.
- Chuyển source-of-truth từ `data.json` sang SQLite.
- Giữ `story_snapshots` theo `channel_id` vì mỗi channel chỉ có 1 truyện.
- Thêm local scheduler/cache metadata để giảm fetch thừa, không cần lưu server.

## Các bước thực hiện
1. Tạo schema SQLite cho state chính của story thay cho `data.json`.
2. Thêm bootstrap/migration để import dữ liệu cũ từ `data.json` vào SQLite.
3. Refactor runner đọc/ghi story state từ SQLite, giữ nguyên fetch flow và send flow.
4. Thêm các field local-first cho scheduler/cache như `next_check_at`, `last_success_at`, `error_count`.
5. Giữ `story_snapshots` theo `channel_id`, tương thích với logic hiện tại.
6. Chạy kiểm tra cơ bản và rà lại ảnh hưởng.

## Trạng thái hiện tại
- Scope đã chốt với chủ nhân.
- Đã thêm bảng `stories` trong SQLite và bootstrap từ `data.json` khi DB chưa có dữ liệu.
- Runner đã đọc/ghi source-of-truth từ SQLite, giữ nguyên flow fetch và Discord send.
- Đã thêm metadata local scheduler: `next_check_date`, `last_success_date`, `error_count`.
- Đã chạy test cơ bản thành công.
