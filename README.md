# CodeForge AI

🤖 **A Comprehensive Local Web-Based AI Development Platform with Multi-Agent Orchestration**

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## 🌟 Features

### 1. Venice AI Integration (Dolphin Uncensored)
- ✅ Integrate Venice AI API with Dolphin uncensored model
- ✅ Support for custom system prompts configuration
- ✅ AI-powered code generation from natural language prompts
- ✅ Streaming responses for real-time feedback

### 2. Multi-Agent Orchestration System
- ✅ Create and manage multiple AI agents
- ✅ Each agent handles different development tasks (frontend, backend, testing, documentation)
- ✅ Agents work in parallel to speed up development
- ✅ Track agent activities and outputs in real-time
- ✅ Recursive agent spawning for specialized tasks

### 3. Project Workspace
- ✅ Dashboard to view all generated projects
- ✅ File browser to navigate project structure
- ✅ Monaco code editor for viewing and editing files
- ✅ Support for multiple file types and syntax highlighting
- ✅ Auto-save and version control

### 4. GitHub Integration
- ✅ Create new repositories
- ✅ Push generated projects to GitHub
- ✅ Manage commits and branches
- ✅ View repository status

### 5. PostgreSQL Database
- ✅ Track all prompts and AI interactions
- ✅ Store project metadata and files
- ✅ Log agent activities and task history
- ✅ Store system prompt configurations

### 6. Real-Time Updates
- ✅ WebSocket support for live agent status updates
- ✅ Real-time code generation streaming
- ✅ Live progress tracking for all operations

---

## 💻 Tech Stack

### Backend
- **Framework:** Python 3.11+ / FastAPI
- **AI Integration:** Venice AI API (Dolphin uncensored model)
- **Database:** PostgreSQL 14+
- **ORM:** SQLAlchemy with Alembic migrations
- **WebSocket:** FastAPI WebSockets
- **GitHub:** PyGithub

### Frontend
- **Framework:** Next.js 14 (React 18)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **Code Editor:** Monaco Editor
- **State Management:** Zustand
- **Data Fetching:** TanStack Query (React Query)
- **UI Components:** Headless UI, Framer Motion
- **WebSocket:** Socket.io-client

---

## 🚀 Quick Start

### Prerequisites

1. **Python 3.11+**
   ```bash
   python --version
   ```

2. **Node.js 18+**
   ```bash
   node --version
   npm --version
   ```

3. **PostgreSQL 14+**
   ```bash
   psql --version
   ```

4. **Git**
   ```bash
   git --version
   ```

### API Credentials

You'll need:
1. **Venice AI API Credentials** - Sign up at [Venice.ai](https://venice.ai)
2. **GitHub Personal Access Token** - Generate at [GitHub Settings](https://github.com/settings/tokens)

---

## 🛠️ Installation

### Option 1: Automated Setup (Recommended)

```bash
cd /home/ubuntu/codeforge_ai
chmod +x setup.sh
./setup.sh
```

### Option 2: Manual Setup

#### 1. Set Up Database

```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql -f database/init.sql

# Verify connection
psql -U codeforge -d codeforge_db -h localhost
```

#### 2. Set Up Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

**Required .env variables:**
```env
VENICE_API_KEY=your_venice_api_key_here
VENICE_API_SECRET=your_venice_api_secret_here
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token_here
GITHUB_USERNAME=your_github_username
DATABASE_URL=postgresql+asyncpg://codeforge:codeforge@localhost:5432/codeforge_db
```

```bash
# Run database migrations
alembic upgrade head

# Start backend server
python main.py
```

Backend will be running at: **http://localhost:8000**

#### 3. Set Up Frontend

```bash
cd ../frontend

# Install dependencies
npm install

# Copy environment template
cp .env.local.example .env.local

# Start development server
npm run dev
```

Frontend will be running at: **http://localhost:3000**

---

## 📚 Usage Guide

### 1. Access the Dashboard

Open your browser and navigate to:
```
http://localhost:3000
```

### 2. Create Your First Project

1. Click on the **Projects** tab in the sidebar
2. Click **+ Create Project**
3. Enter project details:
   - Name
   - Description
   - Framework (optional)
4. Click **Create**

### 3. Generate Code with AI

1. Navigate to the **AI Chat** tab
2. Type your request, for example:
   ```
   Create a React component for a user profile card with avatar, name, and bio
   ```
3. The AI will generate code with syntax highlighting
4. Copy the code or create a file directly from the chat

### 4. Create AI Agents

1. Go to the **Agents** tab
2. Click **+ Create Agent**
3. Configure the agent:
   - **Name:** e.g., "Backend Developer Agent"
   - **Role:** e.g., "Backend Development"
   - **Capabilities:** e.g., "Python", "FastAPI", "Database Design"
   - **System Prompt:** (optional) Custom instructions
4. Click **Create Agent**

Agents will automatically handle assigned tasks and can spawn child agents for specialized work.

### 5. Push to GitHub

1. Open a project
2. Click the **GitHub** icon
3. Configure repository:
   - Repository name
   - Description
   - Public/Private
4. Select files to push
5. Enter commit message
6. Click **Push to GitHub**

---

## 🐛 Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Restart PostgreSQL
sudo systemctl restart postgresql

# Test connection
psql -U codeforge -d codeforge_db -h localhost
```

### Backend Server Issues

```bash
# Check if port 8000 is in use
lsof -i :8000

# View backend logs
cd backend
tail -f logs/app.log

# Restart backend
pkill -f "python main.py"
python main.py
```

### Frontend Issues

```bash
# Clear node_modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install

# Check if port 3000 is in use
lsof -i :3000

# Restart frontend
npm run dev
```

### Venice AI API Issues

1. Verify your API credentials in `backend/.env`
2. Check API quota at [Venice.ai Dashboard](https://venice.ai/dashboard)
3. Test API connection:
   ```bash
   curl -X POST https://api.venice.ai/api/v1/chat/completions \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "X-API-Secret: YOUR_API_SECRET" \
     -H "Content-Type: application/json" \
     -d '{"model": "dolphin-2.9.2-qwen2-72b", "messages": [{"role": "user", "content": "Hello"}]}'
   ```

---

## 📝 API Documentation

### Backend API Endpoints

Once the backend is running, access interactive API docs:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Key Endpoints

#### Chat & AI
- `POST /api/chat` - Stream chat completions
- `POST /api/generate-code` - Generate code from prompt
- `PUT /api/system-prompt` - Update system prompt

#### Agents
- `POST /api/agents/create` - Create new agent
- `GET /api/agents` - List all agents
- `GET /api/agents/{id}` - Get agent details
- `POST /api/agents/{id}/task` - Assign task to agent
- `DELETE /api/agents/{id}` - Terminate agent

#### Projects
- `POST /api/projects` - Create project
- `GET /api/projects` - List projects
- `GET /api/projects/{id}` - Get project details
- `GET /api/projects/{id}/files` - Get project files
- `POST /api/projects/{id}/files` - Save file

#### GitHub
- `POST /api/github/repos` - Create repository
- `POST /api/github/push` - Push files to GitHub
- `GET /api/github/repos` - List repositories
- `GET /api/github/repos/{name}/status` - Get repo status

---

## 🔧 Development

### Project Structure

```
codeforge_ai/
├── backend/
│   ├── app/
│   │   ├── services/          # Core services (Venice AI, Agents, GitHub)
│   │   ├── database/          # Database models and connection
│   │   ├── models/            # Pydantic schemas
│   │   └── websocket/         # WebSocket manager
│   ├── main.py            # FastAPI application
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── app/               # Next.js app directory
│   │   ├── components/        # React components
│   │   ├── lib/               # API client and utilities
│   │   └── store/             # Zustand state management
│   ├── package.json
│   └── .env.local.example
│
├── database/
│   └── init.sql           # Database initialization
│
└── README.md
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Code Quality

```bash
# Backend linting
cd backend
pylint app/

# Frontend linting
cd frontend
npm run lint
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## ❓ FAQ

### Q: Can I use a different AI model?
A: Yes! The system is designed to work with Venice AI's Dolphin model, but you can modify `venice_service.py` to integrate other providers like OpenAI, Anthropic, or local models.

### Q: How do I deploy this to production?
A: For production deployment:
1. Use a production-grade WSGI server (gunicorn with uvicorn workers)
2. Set up proper environment variables
3. Use a reverse proxy (Nginx)
4. Enable HTTPS
5. Use a managed PostgreSQL instance
6. Deploy frontend to Vercel or build static files

### Q: What are the system requirements?
A: Minimum requirements:
- 4GB RAM
- 2 CPU cores
- 10GB disk space
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+

### Q: How much does Venice AI cost?
A: Venice AI offers various pricing tiers. Check [Venice.ai Pricing](https://venice.ai/pricing) for current rates.

### Q: Can agents communicate with each other?
A: Yes! Parent agents can spawn child agents, delegate tasks, and receive results. This enables complex multi-agent workflows.

---

## 📞 Support

For issues, questions, or suggestions:

- **GitHub Issues:** [Create an issue](https://github.com/yourusername/codeforge-ai/issues)
- **Documentation:** [Full Docs](https://github.com/yourusername/codeforge-ai/wiki)

---

## 👏 Acknowledgments

- Venice AI for the Dolphin uncensored model
- FastAPI for the excellent web framework
- Next.js team for the amazing React framework
- Monaco Editor for the powerful code editing experience

---

**✨ Happy Coding with CodeForge AI! ✨**

---

## 📢 Important Notes

> **Localhost Notice:** This application runs on localhost of the computer where it's installed. 
> The backend runs on `http://localhost:8000` and frontend on `http://localhost:3000`.
> To access it remotely, you'll need to deploy it on your own infrastructure or use port forwarding/tunneling.

> **API Keys Security:** Never commit your `.env` files to version control. Always use `.env.example` templates.

> **Database Backups:** Regularly backup your PostgreSQL database to prevent data loss:
> ```bash
> pg_dump -U codeforge codeforge_db > backup_$(date +%Y%m%d_%H%M%S).sql
> ```