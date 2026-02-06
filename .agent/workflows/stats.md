---
description: Xem thống kê và tiến độ projects đã tạo
---

# /stats - Analytics Dashboard

Hiển thị dashboard thống kê tất cả projects đã tạo bởi VibeCoding.

## Cách chạy

// turbo
1. Chạy command sau:
```bash
python new_project.py --stats
```

## Dashboard hiển thị

- 📈 **Tổng quan**: Số projects, hoàn thành, đang làm
- 📋 **Tiến độ từng project**: Progress bar và current phase
- 🛠️ **Tech stack phổ biến**: Thống kê công nghệ được dùng

## Ghi chú

- Data lưu tại: `~/.vibecoding/analytics.json`
- Tiến độ được tính từ `[x]` và `[ ]` trong CONTEXT.md
