# 🚀 HuggingFace Spaces Deployment Guide

Complete guide for deploying CodeForge AI to HuggingFace Spaces.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Deployment Options](#deployment-options)
4. [Step-by-Step Deployment](#step-by-step-deployment)
5. [Configuration](#configuration)
6. [Environment Variables](#environment-variables)
7. [Database Options](#database-options)
8. [Troubleshooting](#troubleshooting)
9. [Updating Your Space](#updating-your-space)
10. [Cost Considerations](#cost-considerations)
11. [Limitations](#limitations)
12. [FAQ](#faq)

---

## 📋 Prerequisites

### Required
- **HuggingFace Account**: [Sign up here](https://huggingface.co/join)
- **HuggingFace API Token**: [Get token here](https://huggingface.co/settings/tokens)
- **Python 3.8+**: For running deployment scripts

### Optional (for full functionality)
- **Venice AI API Key**: For AI code generation ([Venice AI](https://venice.ai))
- **GitHub Personal Access Token**: For GitHub integration ([Create token](https://github.com/settings/tokens))

---

## ⚡ Quick Start

### One-Command Deployment

```bash
# Install dependencies
pip install huggingface_hub

# Set your HuggingFace token
export HF_TOKEN="your-huggingface-token"

# Deploy (creates a new Space)
python deploy_to_huggingface.py --space-name my-codeforge-ai

# Or deploy lightweight Gradio version
python deploy_to_huggingface.py --space-name my-codeforge-ai --gradio-only
```

Your Space will be available at: `https://huggingface.co/spaces/YOUR_USERNAME/my-codeforge-ai`

---

## 🎯 Deployment Options

### Option 1: Full Deployment (Next.js + FastAPI)

**Best for**: Full-featured experience with rich UI

```bash
python deploy_to_huggingface.py --space-name codeforge-full
```

**Includes**:
- Next.js React frontend with Monaco editor
- FastAPI backend with all features
- WebSocket support for real-time updates
- Full project management capabilities

**Resource Usage**:
- Higher memory usage (~4-8GB)
- Longer build time (~5-10 minutes)

### Option 2: Gradio-Only Deployment

**Best for**: Free tier, quick deployment, simple interface

```bash
python deploy_to_huggingface.py --space-name codeforge-lite --gradio-only
```

**Includes**:
- Lightweight Gradio interface
- Core AI chat and code generation
- Project and agent management
- Chat parsing functionality

**Resource Usage**:
- Lower memory usage (~2-4GB)
- Faster build time (~2-5 minutes)

---

## 📝 Step-by-Step Deployment

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/codeforge-ai.git
cd codeforge-ai
```

### Step 2: Install Deployment Dependencies

```bash
pip install huggingface_hub
```

### Step 3: Authenticate with HuggingFace

```bash
# Option A: Set environment variable
export HF_TOKEN="hf_your_token_here"

# Option B: Login interactively
huggingface-cli login
```

### Step 4: Run Deployment Script

```bash
# Basic deployment
python deploy_to_huggingface.py --space-name my-codeforge

# With all options
python deploy_to_huggingface.py \
    --space-name my-codeforge \
    --private \
    --sync-secrets \
    --hardware cpu-basic
```

### Step 5: Configure Secrets

After deployment, go to your Space settings and add:

1. Navigate to: `https://huggingface.co/spaces/YOUR_USERNAME/my-codeforge/settings`
2. Scroll to "Repository secrets"
3. Add:
   - `VENICE_API_KEY`: Your Venice AI key
   - `GITHUB_PERSONAL_ACCESS_TOKEN`: Your GitHub token
   - `SECRET_KEY`: A random secure string

### Step 6: Verify Deployment

1. Wait for build to complete (check "Building" status)
2. Once "Running", click your Space URL
3. Test the interface

---

## ⚙️ Configuration

### Deployment Script Options

| Option | Description | Default |
|--------|-------------|---------|
| `--space-name` | Name for your HF Space | `codeforge-ai` |
| `--username` | HuggingFace username | Auto-detected |
| `--token` | HF API token | `HF_TOKEN` env var |
| `--private` | Make Space private | `false` |
| `--gradio-only` | Deploy Gradio version | `false` |
| `--update` | Update existing Space | `false` |
| `--sync-secrets` | Sync .env to HF secrets | `false` |
| `--hardware` | Hardware tier | `cpu-basic` |
| `--no-monitor` | Skip build monitoring | `false` |

### Hardware Tiers

| Tier | Memory | Cost | Best For |
|------|--------|------|----------|
| `cpu-basic` | 16GB | Free | Gradio version |
| `cpu-upgrade` | 32GB | ~$0.06/hr | Full version |
| `t4-small` | GPU | ~$0.60/hr | Local LLM |
| `t4-medium` | GPU | ~$0.90/hr | Faster LLM |

---

## 🔐 Environment Variables

### Secrets (Sensitive - Set in HF Secrets)

```
VENICE_API_KEY=your-venice-api-key
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_github_token
SECRET_KEY=your-random-secret-key-minimum-32-chars
```

### Variables (Non-sensitive - Set in HF Variables)

```
DATABASE_URL=sqlite:///app/data/codeforge.db
USE_SQLITE=true
HOST=0.0.0.0
PORT=7860
DEBUG=false
GITHUB_USERNAME=your-github-username
DEFAULT_AI_PROVIDER=venice
LOG_LEVEL=INFO
```

### How to Set Variables

1. Go to Space Settings
2. Find "Repository secrets" section
3. Click "New secret" for sensitive values
4. Find "Variables" section for non-sensitive values

---

## 💾 Database Options

### Option 1: SQLite (Recommended for Free Tier)

SQLite is automatically configured for HF Spaces:

```bash
# Automatically used when USE_SQLITE=true
DATABASE_URL=sqlite:///app/data/codeforge.db
```

**Pros**:
- No external dependencies
- Works on free tier
- Persistent within Space

**Cons**:
- Limited concurrent access
- Data lost if Space is deleted

### Option 2: External PostgreSQL

For production use, connect to an external PostgreSQL:

```bash
DATABASE_URL=postgresql://user:password@host:5432/database
USE_SQLITE=false
```

**Recommended Providers**:
- [Supabase](https://supabase.com) - Free tier available
- [Railway](https://railway.app) - Easy setup
- [Neon](https://neon.tech) - Serverless PostgreSQL

### Migrating from PostgreSQL to SQLite

```bash
python backend/app/database/sqlite_adapter.py \
    --migrate "postgresql://user:pass@host:5432/db" \
    --output /app/data/codeforge.db
```

---

## 🔧 Troubleshooting

### Build Failures

**Problem**: Space shows "Build Error"

**Solutions**:
1. Check build logs in Space settings
2. Verify Dockerfile syntax
3. Ensure all dependencies are in requirements.txt
4. Check for missing files

```bash
# Test locally first
docker build -t codeforge-test .
docker run -p 7860:7860 codeforge-test
```

### Runtime Errors

**Problem**: Space crashes after starting

**Solutions**:
1. Check runtime logs
2. Verify environment variables are set
3. Ensure database directory is writable
4. Check memory usage (free tier: 16GB max)

### API Connection Issues

**Problem**: AI chat returns errors

**Solutions**:
1. Verify `VENICE_API_KEY` is set correctly
2. Check API key is valid (test with curl)
3. Ensure no rate limiting

```bash
# Test Venice API
curl -X POST https://api.venice.ai/api/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"dolphin-2.9.2-qwen2-72b","messages":[{"role":"user","content":"Hello"}]}'
```

### Database Issues

**Problem**: "Database locked" or connection errors

**Solutions**:
1. Restart the Space
2. Check SQLite file permissions
3. For high traffic, consider external PostgreSQL

---

## 🔄 Updating Your Space

### Quick Update

```bash
# Update existing Space
python deploy_to_huggingface.py --space-name my-codeforge --update
```

### Using Update Script

```bash
# Make executable
chmod +x update_space.sh

# Run update
./update_space.sh --space-name my-codeforge

# Update Gradio version
./update_space.sh --space-name my-codeforge --gradio

# Update with secrets
./update_space.sh --space-name my-codeforge --sync-secrets
```

### Manual Update via Git

```bash
# Clone your Space
git clone https://huggingface.co/spaces/YOUR_USERNAME/my-codeforge
cd my-codeforge

# Make changes
# ... edit files ...

# Push updates
git add .
git commit -m "Update feature X"
git push
```

---

## 💰 Cost Considerations

### Free Tier

| Feature | Included |
|---------|----------|
| CPU | Basic (2 vCPU) |
| Memory | 16GB |
| Storage | 50GB |
| Bandwidth | Unlimited |
| Uptime | Sleeps after inactivity |

**Note**: Free tier Spaces sleep after ~15 minutes of inactivity. First request after sleep takes ~30-60 seconds.

### Paid Tiers

| Tier | Cost | Benefits |
|------|------|----------|
| CPU Upgrade | ~$0.06/hr | 8 vCPU, 32GB RAM, no sleep |
| T4 Small | ~$0.60/hr | GPU, good for local LLM |
| T4 Medium | ~$0.90/hr | GPU, better for larger models |

### Cost Optimization Tips

1. Use Gradio version for free tier
2. Disable local LLM (uses external Venice AI)
3. Set shorter inactivity timeout
4. Use external database for persistence

---

## ⚠️ Limitations

### Free Tier Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| CPU only | No local GPU LLM | Use Venice AI |
| 16GB memory | Limited concurrent users | Use Gradio version |
| Sleep after inactivity | Slow first request | Upgrade hardware |
| No persistent storage guarantee | Data may be lost | External database |
| Build time limit | Large builds may fail | Optimize Dockerfile |

### Feature Limitations on HF Spaces

| Feature | Status | Notes |
|---------|--------|-------|
| AI Chat | ✅ Full | Via Venice AI |
| Code Generation | ✅ Full | Via Venice AI |
| Local LLM | ⚠️ Limited | Needs GPU tier |
| Project Management | ✅ Full | SQLite storage |
| GitHub Integration | ✅ Full | Set token |
| Real-time WebSocket | ⚠️ Limited | May disconnect |
| File Export | ✅ Full | Works normally |

---

## ❓ FAQ

### Q: How do I get a HuggingFace token?

1. Go to [HuggingFace Settings](https://huggingface.co/settings/tokens)
2. Click "New token"
3. Select "Write" access
4. Copy the token

### Q: Can I use my own domain?

Yes, HuggingFace supports custom domains for paid accounts. Contact HF support.

### Q: How do I backup my data?

```bash
# Export projects via API
curl https://your-space.hf.space/api/projects/export -o backup.zip

# Or use the Export feature in the UI
```

### Q: Can I run this locally instead?

Yes! Use docker-compose:

```bash
docker-compose up --build
# Access at http://localhost:7860
```

### Q: Why is my Space slow to start?

Free tier Spaces sleep after inactivity. The first request wakes it up, which takes 30-60 seconds.

### Q: How do I delete my Space?

1. Go to Space settings
2. Scroll to "Danger Zone"
3. Click "Delete this Space"

---

## 📚 Additional Resources

- [HuggingFace Spaces Documentation](https://huggingface.co/docs/hub/spaces)
- [Docker SDK Guide](https://huggingface.co/docs/hub/spaces-sdks-docker)
- [Venice AI Documentation](https://docs.venice.ai)
- [CodeForge AI GitHub](https://github.com/your-username/codeforge-ai)

---

## 🆘 Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Search [HuggingFace Forums](https://discuss.huggingface.co)
3. Open an issue on [GitHub](https://github.com/your-username/codeforge-ai/issues)

---

*Last updated: February 2026*
