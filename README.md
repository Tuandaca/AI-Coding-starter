# 🚀 AI Coding Starter

> **VibeCoding** - Hệ thống AI Agent hỗ trợ lập trình với Antigravity IDE

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Made with ❤️](https://img.shields.io/badge/Made%20with-❤️-red.svg)](https://github.com)

## ✨ Tính năng

- 🤖 **Multi-Agent System** - Nhiều AI agents chuyên biệt (Frontend, Backend, Security, etc.)
- 📚 **Skill Library** - Thư viện skills cho từng loại dự án
- 🎯 **Project Types** - 7 loại dự án với config tối ưu
- 🛠️ **Tech Stack Presets** - 21+ presets công nghệ phổ biến
- 📋 **Context System** - AI nhớ context dự án giữa các sessions

## 🚀 Cài đặt nhanh

### Windows

```bash
# 1. Clone repo
git clone https://github.com/Tuandaca/AI-Coding-starter.git

# 2. Chạy setup
cd AI-Coding-starter
setup.bat
```

### Mac/Linux

```bash
# 1. Clone repo
git clone https://github.com/Tuandaca/AI-Coding-starter.git

# 2. Chạy setup
cd AI-Coding-starter
chmod +x setup.sh
./setup.sh
```

## 📁 Cấu trúc thư mục

```
AI-coding-starter/
├── .agent/                  # AI Configuration
│   ├── agents/              # AI Agent definitions
│   ├── skills/              # Skill library
│   ├── workflows/           # Workflow commands
│   ├── .shared/             # Shared modules
│   ├── core/                # Core rules
│   ├── rules/               # Base rules
│   └── GEMINI.md            # Main AI config
├── new_project.py           # Interactive project creator
├── setup.bat                # Windows setup
├── setup.sh                 # Mac/Linux setup
└── README.md
```

## 🎮 Cách sử dụng

### 1. Tạo dự án mới

```bash
python new_project.py
```

Wizard sẽ hỏi:
- Tên dự án
- Đường dẫn
- Loại dự án (Personal Web, E-commerce, SaaS, Mobile, Game, AI/ML, Full-Stack)
- Tech Stack preset

### 2. Mở project trong Antigravity IDE

```bash
# Mở folder project
# AI sẽ tự động đọc .agent/GEMINI.md
```

### 3. Bắt đầu code!

```
Bạn: Tạo trang login cho tôi
AI: (Hiểu context từ GEMINI.md) → Tạo code đúng tech stack!
```

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

## 📋 Context System

File `.agent/CONTEXT.md` giúp AI nhớ:
- Tiến độ dự án
- Quyết định đã thực hiện
- Issues đang tồn tại
- Next steps

**Tip:** Cuối mỗi session, nói với AI:
```
Cập nhật CONTEXT.md với tiến độ hôm nay
```

## 🤝 Đóng góp

Contributions are welcome! Hãy:
1. Fork repo
2. Tạo branch mới
3. Commit changes
4. Tạo Pull Request

## 📄 License

MIT License - Xem file [LICENSE](LICENSE) để biết thêm chi tiết.

## 🙏 Credits

- Được phát triển cho cộng đồng Việt Nam 🇻🇳
- Sử dụng với [Antigravity IDE](https://antigravity.dev)

---

**Made with ❤️ by Vietnamese Developers**
