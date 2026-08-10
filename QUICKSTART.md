# 🚀 CodeForge AI - Quick Start Guide

## Prerequisites Checklist

Before you begin, ensure you have:

- [ ] **Python 3.11+** installed ([Download](https://python.org))
- [ ] **Node.js 18+** installed ([Download](https://nodejs.org))
- [ ] **PostgreSQL 14+** installed ([Download](https://postgresql.org))
- [ ] **Venice AI API Key** ([Sign up](https://venice.ai))
- [ ] **GitHub Personal Access Token** ([Generate](https://github.com/settings/tokens))

---

## ⚡ 5-Minute Setup

### Step 1: Run Automated Setup

**On Linux/Mac:**
```bash
cd /home/ubuntu/codeforge_ai
chmod +x setup.sh
./setup.sh
```

**On Windows:**
```powershell
cd C:\path\to\codeforge_ai
.\setup.ps1
```

### Step 2: Configure API Credentials

Edit `backend/.env` with your credentials:

```bash
nano backend/.env
```

Add:
```env
VENICE_API_KEY=your_venice_api_key_here
VENICE_API_SECRET=your_venice_api_secret_here
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here
GITHUB_USERNAME=your_github_username
```

### Step 3: Start Backend

**Terminal 1:**
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python main.py
```

You should see:
```
🚀 CodeForge AI Backend Starting...
✅ Database connected
✅ Services initialized
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 4: Start Frontend

**Terminal 2:**
```bash
cd frontend
npm run dev
```

You should see:
```
▶ Local:    http://localhost:3000
▶ Network:  http://192.168.x.x:3000
```

### Step 5: Open Application

Open your browser and navigate to:
```
http://localhost:3000
```

---

## 🎯 First Tasks

### 1. Create Your First Project

1. Click **Projects** in the sidebar
2. Click the **+** button
3. Enter:
   - **Name:** "My First Project"
   - **Description:** "Testing CodeForge AI"
   - **Framework:** Select "React" or "Python"
4. Click **Create Project**

### 2. Generate Code with AI

1. Click **AI Chat** in the sidebar
2. Type a prompt:
   ```
   Create a React component that displays a user profile with avatar, name, email, and a follow button
   ```
3. Watch the AI generate code in real-time!
4. Copy the code or save it to your project

### 3. Create an AI Agent

1. Click **Agents** in the sidebar
2. Click the **+** button
3. Configure:
   - **Name:** "Frontend Developer"
   - **Role:** "Frontend Development"
   - **Capabilities:** Add "React", "TypeScript", "CSS"
4. Click **Create Agent**

Your agent is now ready to handle tasks!

### 4. Push to GitHub

1. Select your project
2. Click the **GitHub** icon
3. Create a new repository:
   - **Name:** "my-first-codeforge-project"
   - **Description:** "Created with CodeForge AI"
   - **Private:** Choose Yes or No
4. Click **Create & Push**

Your code is now on GitHub!

---

## 🐛 Common Issues

### Issue: "Database connection failed"

**Solution:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL
sudo systemctl start postgresql

# Create database
sudo -u postgres psql -c "CREATE DATABASE codeforge_db;"
sudo -u postgres psql -c "CREATE USER codeforge WITH PASSWORD 'codeforge';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE codeforge_db TO codeforge;"
```

### Issue: "Port 8000 already in use"

**Solution:**
```bash
# Find and kill the process
lsof -ti:8000 | xargs kill -9

# Or change the port in backend/main.py
```

### Issue: "Venice AI API error"

**Solution:**
1. Verify your API key in `backend/.env`
2. Check your API quota at [Venice.ai Dashboard](https://venice.ai/dashboard)
3. Test API connection:
   ```bash
   curl -X POST https://api.venice.ai/api/v1/chat/completions \
     -H "Authorization: Bearer YOUR_KEY" \
     -H "X-API-Secret: YOUR_SECRET" \
     -d '{"model":"dolphin-2.9.2-qwen2-72b","messages":[{"role":"user","content":"test"}]}'
   ```

### Issue: "npm install fails"

**Solution:**
```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

---

## 📚 Learn More

- **Full Documentation:** See [README.md](README.md)
- **API Reference:** http://localhost:8000/docs (when backend is running)
- **Venice AI Docs:** https://docs.venice.ai
- **GitHub Integration:** See backend configuration

---

## ✨ Pro Tips

1. **System Prompts:** Customize agent behavior by editing system prompts in the Agent creation form

2. **Code Editor Shortcuts:**
   - `Ctrl+S` / `Cmd+S` - Save file
   - `Ctrl+F` / `Cmd+F` - Find in file
   - `Ctrl+/` / `Cmd+/` - Toggle comment

3. **Agent Spawning:** Agents can automatically spawn child agents for specialized tasks. Watch the agent panel for spawning activity!

4. **Real-time Updates:** WebSocket connection provides live updates. Check the green indicator in the sidebar.

5. **Backup Your Work:**
   ```bash
   # Backup database
   pg_dump -U codeforge codeforge_db > backup.sql
   
   # Export projects via GitHub integration
   ```

---

## 👍 Next Steps

Now that you're set up, try:

1. **Generate a Full App:** Ask the AI to create a complete application
2. **Multi-Agent Workflow:** Create multiple agents and assign them different parts of a project
3. **GitHub Automation:** Set up automatic pushing of generated code
4. **Custom System Prompts:** Experiment with different agent personalities and capabilities

---

## 📢 Important Notes

> **Localhost Notice:** This application runs on your local machine:
> - Backend: http://localhost:8000
> - Frontend: http://localhost:3000
> 
> To access remotely, you'll need to deploy on a server or use port forwarding.

> **API Usage:** Monitor your Venice AI API usage to avoid unexpected charges.

> **Security:** Never commit `.env` files to version control!

---

**✨ You're ready to build with CodeForge AI! ✨**

Happy coding! 🚀