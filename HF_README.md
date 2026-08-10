---
title: CodeForge AI
emoji: 🔧
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
app_port: 7860
suggested_hardware: cpu-basic
short_description: AI-powered code generation and development platform
tags:
  - code-generation
  - ai-assistant
  - development-tools
  - fastapi
  - nextjs
---

# 🔧 CodeForge AI

AI-powered code generation and development platform with multi-agent orchestration, project management, and GitHub integration.

## ✨ Features

- **🤖 AI Code Generation** - Generate code using Venice AI or local LLMs
- **👥 Multi-Agent Orchestration** - Create and manage AI agents with specialized roles
- **📁 Project Management** - Full project workspace with Monaco code editor
- **🔗 GitHub Integration** - Push code directly to GitHub repositories
- **📊 Code Quality Analysis** - Automated complexity and security analysis
- **📄 Chat Parser** - Extract code from AI chat transcripts
- **⚡ Workflow Generator** - Create GitHub Actions CI/CD pipelines

## 🚀 Quick Start

1. The application will automatically start when the Space launches
2. Navigate to the interface in your browser
3. Configure your API keys in Settings (optional)
4. Start generating code with AI!

## ⚙️ Configuration

Set these environment variables in Space Settings → Variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `VENICE_API_KEY` | Venice AI API key for code generation | Optional |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub token for repo integration | Optional |
| `GITHUB_USERNAME` | Your GitHub username | Optional |
| `SECRET_KEY` | Application secret key | Recommended |

## 🏗️ Architecture

- **Backend**: FastAPI (Python 3.11)
- **Frontend**: Next.js (React)
- **Database**: SQLite (HF Spaces) / PostgreSQL (external)
- **AI**: Venice AI API / Local LLMs

## 📝 API Documentation

Once running, access the API docs at:
- Swagger UI: `/docs`
- ReDoc: `/redoc`

## 🔒 Privacy

- All data is stored locally in the Space
- API keys are stored securely and never logged
- No data is sent to external services except configured AI providers

## 📚 Documentation

- [Full Documentation](https://github.com/your-username/codeforge-ai)
- [API Reference](https://github.com/your-username/codeforge-ai/docs)

## 📄 License

MIT License - See LICENSE file for details
