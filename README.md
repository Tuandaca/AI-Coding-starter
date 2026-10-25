# 🚀 AI Coding Starter

> **VibeCoding** - Hệ thống AI Agent hỗ trợ lập trình với Antigravity IDE

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Made with ❤️](https://img.shields.io/badge/Made%20with-❤️-red.svg)](https://github.com)

---

## ⚠️ Lưu ý quan trọng

Project này được xây dựng **dựa trên** [google-antigravity](https://github.com/Dokhacgiakhoa/google-antigravity) bởi **@Dokhacgiakhoa**.

**Tôi KHÔNG tạo ra hệ thống Agent gốc** - tôi chỉ đóng góp thêm:
- 🎯 **Interactive Project Creator** - Wizard tạo dự án nhanh
- 🛠️ **Tech Stack Presets** - 21+ presets công nghệ
- 📋 **Context System** - AI nhớ context giữa sessions
- 🚀 **Setup Script** - 1-click setup cho Windows/Mac/Linux

Toàn bộ credit về Multi-Agent System, Skills, và Workflows thuộc về tác giả gốc.

---

## 🔧 Cách hoạt động

```
┌─────────────────────────────────────────────────────────────┐
│  Bạn chạy: setup.bat                                        │
│           ↓                                                 │
│  Script tự động clone template từ:                          │
│  https://github.com/Dokhacgiakhoa/google-antigravity        │
│           ↓                                                 │
│  Setup thêm các tools của repo này:                         │
│  - new_project.py (Interactive wizard)                      │
│  - Tech Stack Presets                                       │
│  - Context System                                           │
│           ↓                                                 │
│  Bạn có thể tạo projects với: python new_project.py         │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ Tính năng

### Từ [google-antigravity](https://github.com/Dokhacgiakhoa/google-antigravity) (Original):
- 🤖 **Multi-Agent System** - Nhiều AI agents chuyên biệt
- 📚 **Skill Library** - Thư viện skills đa dạng
- 📂 **Shared Modules** - Database, API, Security standards

### Tôi đóng góp thêm (This repo):
- 🎯 **Project Types** - 7 loại dự án với config tối ưu
- 🛠️ **Tech Stack Presets** - 21+ presets công nghệ phổ biến
- 📋 **Context System** - AI nhớ context dự án giữa các sessions
- 🚀 **Setup Script** - Tự động setup 1-click

---

## 🚀 Cài đặt nhanh / Quick Setup

### 🇺🇸 English Instructions

1. **Clone this repository** (or download as ZIP and extract):
    ```bash
    git clone https://github.com/Tuandaca/AI-Coding-starter.git
    cd AI-Coding-starter
    ```

2. **Run the Setup Wizard**:
    - **Windows**: Double-click `setup.bat`. You can customize the workspace path and the master template URL during the setup.
    - **Mac/Linux**: Run `./setup.sh` in the terminal.

3. **Start the Tool**:
    - **Windows**: After setup is complete, simply double-click the customized `NewPJ.bat` shortcut to instantly launch the beautiful interactive UI.
    - You can also run it manually anywhere using `python new_project.py`.

### 🇻🇳 Hướng dẫn Tiếng Việt

1. **Tải mã nguồn này về** (Dùng lệnh git clone bên dưới hoặc tải file ZIP về giải nén):
    ```bash
    git clone https://github.com/Tuandaca/AI-Coding-starter.git
    cd AI-Coding-starter
    ```

2. **Chạy trình Cài đặt (Setup Wizard)**:
    - **Windows**: Nhấn đúp (Double-click) vào file `setup.bat`. Trình cài đặt sẽ cho phép bạn tự định nghĩa thư mục làm việc (mặc định ở ổ C) và tự động kéo hệ thống "Master Template" chứa các Agents. Nếu link tải Agent bị lỗi, script sẽ hỏi bạn nhập link dự phòng.
    - **Mac/Linux**: Mở terminal, cấp quyền thực thi `chmod +x setup.sh` và chạy `./setup.sh`.

3. **Khởi chạy Hệ thống**:
    - **Windows**: Sau khi cài ráp thành công, thư mục sẽ xuất hiện 1 file tên là `NewPJ.bat`. Từ giờ mỗi khi cần tạo dự án, bạn chỉ việc bấm đúp vào file này, terminal sẽ được làm sạch tự động để hiện bảng chọn Agent rất trực quan.
    - **Toàn bộ hệ điều hành**: Gọi thủ công bằng lệnh `python new_project.py`.

---

## 📁 Cấu trúc thư mục

```
AI-Coding-starter/
├── .agent/                  # AI Configuration (from original)
│   ├── agents/              # AI Agent definitions
│   ├── skills/              # Skill library
│   ├── workflows/           # Workflow commands
│   └── GEMINI.md            # Main AI config
├── new_project.py           # ⭐ Interactive project creator (MY CONTRIBUTION)
├── setup.bat                # ⭐ Windows setup (MY CONTRIBUTION)
├── setup.sh                 # ⭐ Mac/Linux setup (MY CONTRIBUTION)
└── README.md
```

---

## 🎮 Cách sử dụng

### 1. Tạo dự án mới

```bash
python new_project.py
```

Wizard sẽ hỏi:
- Tên dự án
- Đường dẫn
- Loại dự án (7 types)
- Tech Stack preset (21+ options)

### 2. Mở project trong Antigravity IDE

AI sẽ tự động đọc `.agent/GEMINI.md` và bắt đầu hỗ trợ!

---

## 🎯 Loại dự án hỗ trợ

| Type | Mô tả | Tech Stack mặc định |
|------|-------|---------------------|
| 🌐 Personal Web | Portfolio, Landing page | Next.js + TailwindCSS |
| 🛒 E-commerce | Online store | Next.js + Prisma + Stripe |
| ☁️ SaaS | Software as a Service | Next.js + Supabase |
| 📱 Mobile | iOS/Android apps | React Native + Expo |
| 🎮 Game Dev | 2D/3D games | Phaser / Godot / Unity |
| 🤖 AI/ML | AI applications | Python + FastAPI + LangChain |
| 🔥 Full-Stack | Complete web app | Next.js + Prisma + PostgreSQL |

---

## 📋 Context System

File `.agent/CONTEXT.md` giúp AI nhớ tiến độ dự án giữa các sessions.

**Tip:** Cuối mỗi session, nói với AI:
```
Cập nhật CONTEXT.md với tiến độ hôm nay
```

---

## 🙏 Credits & Acknowledgments

### Original Authors:
- **[@Dokhacgiakhoa](https://github.com/Dokhacgiakhoa)** - Tác giả hệ thống [google-antigravity](https://github.com/Dokhacgiakhoa/google-antigravity)
- Multi-Agent System, Skills, Workflows - Toàn bộ credit thuộc về tác giả gốc

### This Repository:
- **[@Tuandaca](https://github.com/Tuandaca)** - Interactive Project Creator, Tech Stack Presets, Context System, Setup Scripts

### Tools Used:
- [Antigravity IDE](https://antigravity.dev) - AI Coding IDE

---

## 🤝 Đóng góp

Contributions are welcome! Hãy:
1. Fork repo
2. Tạo branch mới
3. Commit changes
4. Tạo Pull Request

---

## 📄 License

MIT License - Xem file [LICENSE](LICENSE) để biết thêm chi tiết.

---

**Made with ❤️ for Vietnamese Developer Community 🇻🇳**
