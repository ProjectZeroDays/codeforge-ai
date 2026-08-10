"""
Project Templates Library Service
Provides pre-built project templates for quick project creation
"""

import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

logger = logging.getLogger(__name__)


# ============================================================
# Pre-built Templates
# ============================================================

BUILT_IN_TEMPLATES = [
    # 1. FastAPI REST API Template
    {
        "name": "FastAPI REST API",
        "description": "A production-ready REST API with FastAPI, SQLAlchemy, Alembic, and JWT authentication",
        "category": "rest_api",
        "language": "python",
        "framework": "fastapi",
        "tags": ["api", "rest", "jwt", "sqlalchemy", "async"],
        "version": "1.0.0",
        "dependencies": {
            "python": ">=3.9",
            "packages": [
                "fastapi>=0.100.0",
                "uvicorn[standard]>=0.22.0",
                "sqlalchemy>=2.0.0",
                "alembic>=1.11.0",
                "python-jose[cryptography]>=3.3.0",
                "passlib[bcrypt]>=1.7.4",
                "python-multipart>=0.0.6",
                "asyncpg>=0.28.0",
                "pydantic>=2.0.0",
                "pydantic-settings>=2.0.0"
            ]
        },
        "scripts": {
            "dev": "uvicorn main:app --reload --port 8000",
            "start": "uvicorn main:app --host 0.0.0.0 --port 8000",
            "migrate": "alembic upgrade head",
            "test": "pytest -v"
        },
        "files": [
            {
                "path": "main.py",
                "content": '''"""FastAPI Application Entry Point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router
from app.database.connection import init_db

app = FastAPI(
    title="API Service",
    description="Production-ready REST API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1")

@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
'''
            },
            {
                "path": "app/__init__.py",
                "content": '"""Application Package"""'
            },
            {
                "path": "app/api/__init__.py",
                "content": '''"""API Routes"""
from fastapi import APIRouter
from app.api import users, auth

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(users.router, prefix="/users", tags=["Users"])
'''
            },
            {
                "path": "app/api/auth.py",
                "content": '''"""Authentication Routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.services.auth_service import AuthService
from app.schemas.auth import Token, UserCreate

router = APIRouter()
auth_service = AuthService()

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await auth_service.authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth_service.create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/register")
async def register(user: UserCreate):
    return await auth_service.register_user(user)
'''
            },
            {
                "path": "app/api/users.py",
                "content": '''"""User Routes"""
from fastapi import APIRouter, Depends
from app.services.user_service import UserService
from app.dependencies import get_current_user

router = APIRouter()
user_service = UserService()

@router.get("/me")
async def get_me(current_user = Depends(get_current_user)):
    return current_user

@router.get("/")
async def list_users():
    return await user_service.get_all()
'''
            },
            {
                "path": "app/database/__init__.py",
                "content": '"""Database Package"""'
            },
            {
                "path": "app/database/connection.py",
                "content": '''"""Database Connection"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/dbname")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
'''
            },
            {
                "path": "app/database/models.py",
                "content": '''"""Database Models"""
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.database.connection import Base
import uuid

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
'''
            },
            {
                "path": "app/schemas/__init__.py",
                "content": '"""Pydantic Schemas"""'
            },
            {
                "path": "app/schemas/auth.py",
                "content": '''"""Auth Schemas"""
from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    is_active: bool
'''
            },
            {
                "path": "app/services/__init__.py",
                "content": '"""Services Package"""'
            },
            {
                "path": "app/services/auth_service.py",
                "content": '''"""Authentication Service"""
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
import os

class AuthService:
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
'''
            },
            {
                "path": "app/dependencies.py",
                "content": '''"""FastAPI Dependencies"""
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import os

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"email": email}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
'''
            },
            {
                "path": "requirements.txt",
                "content": '''fastapi>=0.100.0
uvicorn[standard]>=0.22.0
sqlalchemy>=2.0.0
alembic>=1.11.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
asyncpg>=0.28.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
httpx>=0.24.0
'''
            },
            {
                "path": ".env.example",
                "content": '''DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
SECRET_KEY=your-secret-key-here
DEBUG=true
'''
            },
            {
                "path": ".gitignore",
                "content": '''__pycache__/
*.pyc
.env
venv/
.pytest_cache/
'''
            },
            {
                "path": "alembic.ini",
                "content": '''[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://user:password@localhost/dbname

[loggers]
keys = root,sqlalchemy,alembic
'''
            },
            {
                "path": "Dockerfile",
                "content": '''FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
'''
            }
        ]
    },
    
    # 2. Express.js REST API
    {
        "name": "Express.js REST API",
        "description": "Node.js REST API with Express, Prisma ORM, and JWT authentication",
        "category": "rest_api",
        "language": "javascript",
        "framework": "express",
        "tags": ["api", "rest", "jwt", "prisma", "nodejs"],
        "version": "1.0.0",
        "dependencies": {
            "node": ">=18.0.0",
            "packages": {
                "express": "^4.18.0",
                "prisma": "^5.0.0",
                "@prisma/client": "^5.0.0",
                "jsonwebtoken": "^9.0.0",
                "bcryptjs": "^2.4.3",
                "dotenv": "^16.0.0",
                "cors": "^2.8.5"
            },
            "devPackages": {
                "nodemon": "^3.0.0",
                "jest": "^29.0.0"
            }
        },
        "scripts": {
            "dev": "nodemon src/index.js",
            "start": "node src/index.js",
            "prisma:migrate": "npx prisma migrate dev",
            "test": "jest"
        },
        "files": [
            {
                "path": "src/index.js",
                "content": '''require('dotenv').config();
const express = require('express');
const cors = require('cors');
const authRoutes = require('./routes/auth');
const userRoutes = require('./routes/users');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// Routes
app.use('/api/auth', authRoutes);
app.use('/api/users', userRoutes);

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
'''
            },
            {
                "path": "src/routes/auth.js",
                "content": '''const express = require('express');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { PrismaClient } = require('@prisma/client');

const router = express.Router();
const prisma = new PrismaClient();

router.post('/register', async (req, res) => {
  try {
    const { email, password } = req.body;
    const hashedPassword = await bcrypt.hash(password, 10);
    const user = await prisma.user.create({
      data: { email, password: hashedPassword }
    });
    res.status(201).json({ id: user.id, email: user.email });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

router.post('/login', async (req, res) => {
  try {
    const { email, password } = req.body;
    const user = await prisma.user.findUnique({ where: { email } });
    if (!user || !await bcrypt.compare(password, user.password)) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }
    const token = jwt.sign({ id: user.id }, process.env.JWT_SECRET, { expiresIn: '1h' });
    res.json({ token });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
'''
            },
            {
                "path": "src/routes/users.js",
                "content": '''const express = require('express');
const { PrismaClient } = require('@prisma/client');
const authMiddleware = require('../middleware/auth');

const router = express.Router();
const prisma = new PrismaClient();

router.get('/me', authMiddleware, async (req, res) => {
  const user = await prisma.user.findUnique({
    where: { id: req.userId },
    select: { id: true, email: true, createdAt: true }
  });
  res.json(user);
});

router.get('/', async (req, res) => {
  const users = await prisma.user.findMany({
    select: { id: true, email: true, createdAt: true }
  });
  res.json(users);
});

module.exports = router;
'''
            },
            {
                "path": "src/middleware/auth.js",
                "content": '''const jwt = require('jsonwebtoken');

module.exports = (req, res, next) => {
  const authHeader = req.headers.authorization;
  if (!authHeader) {
    return res.status(401).json({ error: 'No token provided' });
  }
  
  const token = authHeader.split(' ')[1];
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.userId = decoded.id;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
};
'''
            },
            {
                "path": "prisma/schema.prisma",
                "content": '''datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

model User {
  id        String   @id @default(uuid())
  email     String   @unique
  password  String
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}
'''
            },
            {
                "path": "package.json",
                "content": '''{
  "name": "express-api",
  "version": "1.0.0",
  "main": "src/index.js",
  "scripts": {
    "dev": "nodemon src/index.js",
    "start": "node src/index.js",
    "prisma:migrate": "npx prisma migrate dev",
    "test": "jest"
  },
  "dependencies": {
    "@prisma/client": "^5.0.0",
    "bcryptjs": "^2.4.3",
    "cors": "^2.8.5",
    "dotenv": "^16.0.0",
    "express": "^4.18.0",
    "jsonwebtoken": "^9.0.0"
  },
  "devDependencies": {
    "jest": "^29.0.0",
    "nodemon": "^3.0.0",
    "prisma": "^5.0.0"
  }
}
'''
            },
            {
                "path": ".env.example",
                "content": '''DATABASE_URL="postgresql://user:password@localhost:5432/mydb"
JWT_SECRET="your-jwt-secret"
PORT=3000
'''
            },
            {
                "path": ".gitignore",
                "content": '''node_modules/
.env
'''
            },
            {
                "path": "Dockerfile",
                "content": '''FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npx prisma generate
EXPOSE 3000
CMD ["node", "src/index.js"]
'''
            }
        ]
    },
    
    # 3. Next.js Web Application
    {
        "name": "Next.js Full-Stack App",
        "description": "Modern React application with Next.js 14, App Router, Tailwind CSS, and API routes",
        "category": "web_app",
        "language": "typescript",
        "framework": "nextjs",
        "tags": ["react", "nextjs", "typescript", "tailwind", "fullstack"],
        "version": "1.0.0",
        "dependencies": {
            "node": ">=18.0.0",
            "packages": {
                "next": "^14.0.0",
                "react": "^18.0.0",
                "react-dom": "^18.0.0",
                "@tanstack/react-query": "^5.0.0",
                "zustand": "^4.0.0",
                "lucide-react": "^0.300.0"
            },
            "devPackages": {
                "typescript": "^5.0.0",
                "@types/react": "^18.0.0",
                "tailwindcss": "^3.0.0",
                "autoprefixer": "^10.0.0",
                "postcss": "^8.0.0"
            }
        },
        "scripts": {
            "dev": "next dev",
            "build": "next build",
            "start": "next start",
            "lint": "next lint"
        },
        "files": [
            {
                "path": "src/app/layout.tsx",
                "content": '''import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'My App',
  description: 'Built with Next.js',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
'''
            },
            {
                "path": "src/app/page.tsx",
                "content": '''export default function Home() {
  return (
    <main className="min-h-screen p-8">
      <h1 className="text-4xl font-bold mb-4">Welcome to My App</h1>
      <p className="text-gray-600">Get started by editing src/app/page.tsx</p>
    </main>
  );
}
'''
            },
            {
                "path": "src/app/globals.css",
                "content": '''@tailwind base;
@tailwind components;
@tailwind utilities;
'''
            },
            {
                "path": "src/app/providers.tsx",
                "content": ''''use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
'''
            },
            {
                "path": "src/app/api/hello/route.ts",
                "content": '''import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({ message: 'Hello, World!' });
}
'''
            },
            {
                "path": "src/store/useStore.ts",
                "content": '''import { create } from 'zustand';

interface AppState {
  count: number;
  increment: () => void;
  decrement: () => void;
}

export const useStore = create<AppState>((set) => ({
  count: 0,
  increment: () => set((state) => ({ count: state.count + 1 })),
  decrement: () => set((state) => ({ count: state.count - 1 })),
}));
'''
            },
            {
                "path": "tailwind.config.ts",
                "content": '''import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
'''
            },
            {
                "path": "next.config.js",
                "content": '''/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
};

module.exports = nextConfig;
'''
            },
            {
                "path": "tsconfig.json",
                "content": '''{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
'''
            },
            {
                "path": "package.json",
                "content": '''{
  "name": "nextjs-app",
  "version": "1.0.0",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0",
    "@tanstack/react-query": "^5.0.0",
    "zustand": "^4.0.0",
    "lucide-react": "^0.300.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.0.0",
    "@types/react-dom": "^18.0.0",
    "autoprefixer": "^10.0.0",
    "postcss": "^8.0.0",
    "tailwindcss": "^3.0.0",
    "typescript": "^5.0.0"
  }
}
'''
            },
            {
                "path": ".gitignore",
                "content": '''node_modules/
.next/
.env.local
'''
            }
        ]
    },
    
    # 4. Python CLI Tool (Click)
    {
        "name": "Python CLI Tool",
        "description": "Command-line interface application with Click, rich output, and configuration management",
        "category": "cli_tool",
        "language": "python",
        "framework": "click",
        "tags": ["cli", "command-line", "click", "rich"],
        "version": "1.0.0",
        "dependencies": {
            "python": ">=3.9",
            "packages": [
                "click>=8.1.0",
                "rich>=13.0.0",
                "pydantic>=2.0.0",
                "pyyaml>=6.0.0",
                "python-dotenv>=1.0.0"
            ]
        },
        "scripts": {
            "install": "pip install -e .",
            "test": "pytest -v"
        },
        "files": [
            {
                "path": "src/cli/__init__.py",
                "content": '"""CLI Application"""\n__version__ = "1.0.0"'
            },
            {
                "path": "src/cli/main.py",
                "content": '''"""Main CLI Entry Point"""
import click
from rich.console import Console
from rich.table import Table
from .config import load_config, save_config
from .commands import process, analyze

console = Console()

@click.group()
@click.version_option()
@click.option('--debug/--no-debug', default=False, help='Enable debug mode')
@click.pass_context
def cli(ctx, debug):
    """My CLI Tool - A powerful command-line utility."""
    ctx.ensure_object(dict)
    ctx.obj['DEBUG'] = debug
    ctx.obj['CONFIG'] = load_config()

@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('-o', '--output', type=click.Path(), help='Output file path')
@click.pass_context
def process_file(ctx, input_file, output):
    """Process a file and generate output."""
    config = ctx.obj['CONFIG']
    console.print(f"[bold blue]Processing:[/] {input_file}")
    result = process(input_file, output, config)
    console.print(f"[bold green]Done![/] {result}")

@cli.command()
@click.argument('target')
@click.option('--format', '-f', type=click.Choice(['json', 'yaml', 'table']), default='table')
@click.pass_context
def analyze_target(ctx, target, format):
    """Analyze a target and display results."""
    results = analyze(target)
    
    if format == 'table':
        table = Table(title="Analysis Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        for key, value in results.items():
            table.add_row(key, str(value))
        console.print(table)
    else:
        console.print(results)

@cli.command()
@click.option('--key', prompt='Config key')
@click.option('--value', prompt='Config value')
def config(key, value):
    """Set a configuration value."""
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
    console.print(f"[green]Set {key} = {value}[/]")

def main():
    cli(obj={})

if __name__ == '__main__':
    main()
'''
            },
            {
                "path": "src/cli/config.py",
                "content": '''"""Configuration Management"""
import os
import yaml
from pathlib import Path

CONFIG_DIR = Path.home() / ".mycli"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

def load_config() -> dict:
    """Load configuration from file."""
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f) or {}

def save_config(config: dict):
    """Save configuration to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f)
'''
            },
            {
                "path": "src/cli/commands.py",
                "content": '''"""CLI Commands Implementation"""
from pathlib import Path

def process(input_file: str, output: str | None, config: dict) -> str:
    """Process a file."""
    # Implementation here
    return f"Processed {input_file}"

def analyze(target: str) -> dict:
    """Analyze a target."""
    return {
        "target": target,
        "status": "healthy",
        "items_found": 42
    }
'''
            },
            {
                "path": "setup.py",
                "content": '''from setuptools import setup, find_packages

setup(
    name="mycli",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "click>=8.1.0",
        "rich>=13.0.0",
        "pyyaml>=6.0.0",
    ],
    entry_points={
        "console_scripts": [
            "mycli=cli.main:main",
        ],
    },
)
'''
            },
            {
                "path": "requirements.txt",
                "content": '''click>=8.1.0
rich>=13.0.0
pydantic>=2.0.0
pyyaml>=6.0.0
python-dotenv>=1.0.0
pytest>=7.0.0
'''
            },
            {
                "path": ".gitignore",
                "content": '''__pycache__/
*.egg-info/
dist/
build/
.env
venv/
'''
            }
        ]
    },
    
    # 5. Machine Learning Project
    {
        "name": "ML Project Template",
        "description": "Machine Learning project with scikit-learn, pandas, and MLflow tracking",
        "category": "machine_learning",
        "language": "python",
        "framework": "scikit-learn",
        "tags": ["ml", "machine-learning", "scikit-learn", "mlflow", "pandas"],
        "version": "1.0.0",
        "dependencies": {
            "python": ">=3.9",
            "packages": [
                "scikit-learn>=1.3.0",
                "pandas>=2.0.0",
                "numpy>=1.24.0",
                "mlflow>=2.8.0",
                "matplotlib>=3.7.0",
                "seaborn>=0.12.0",
                "joblib>=1.3.0"
            ]
        },
        "scripts": {
            "train": "python src/train.py",
            "evaluate": "python src/evaluate.py",
            "serve": "mlflow models serve -m models/latest -p 5000"
        },
        "files": [
            {
                "path": "src/train.py",
                "content": '''"""Model Training Script"""
import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import pandas as pd
import joblib
from pathlib import Path

from data.loader import load_data
from features.build_features import build_features

def train_model(data_path: str, model_path: str = "models/model.joblib"):
    # Load and prepare data
    df = load_data(data_path)
    X, y = build_features(df)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    with mlflow.start_run():
        # Train model
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        # Evaluate
        predictions = model.predict(X_test)
        accuracy = accuracy_score(y_test, predictions)
        
        # Log metrics
        mlflow.log_param("n_estimators", 100)
        mlflow.log_metric("accuracy", accuracy)
        mlflow.sklearn.log_model(model, "model")
        
        # Save model
        Path(model_path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, model_path)
        
        print(f"Model accuracy: {accuracy:.4f}")
        print(classification_report(y_test, predictions))

if __name__ == "__main__":
    train_model("data/raw/dataset.csv")
'''
            },
            {
                "path": "src/predict.py",
                "content": '''"""Prediction Script"""
import joblib
import pandas as pd
from features.build_features import build_features

def predict(model_path: str, data: pd.DataFrame):
    model = joblib.load(model_path)
    X, _ = build_features(data)
    return model.predict(X)
'''
            },
            {
                "path": "src/data/__init__.py",
                "content": '"""Data Module"""'
            },
            {
                "path": "src/data/loader.py",
                "content": '''"""Data Loading Utilities"""
import pandas as pd

def load_data(path: str) -> pd.DataFrame:
    """Load dataset from CSV."""
    return pd.read_csv(path)
'''
            },
            {
                "path": "src/features/__init__.py",
                "content": '"""Feature Engineering Module"""'
            },
            {
                "path": "src/features/build_features.py",
                "content": '''"""Feature Engineering"""
import pandas as pd
from sklearn.preprocessing import StandardScaler

def build_features(df: pd.DataFrame):
    """Build features from raw data."""
    # Example feature engineering
    X = df.drop('target', axis=1) if 'target' in df.columns else df
    y = df['target'] if 'target' in df.columns else None
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    return X_scaled, y
'''
            },
            {
                "path": "notebooks/exploration.ipynb",
                "content": '''{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": ["# Data Exploration Notebook"]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": ["import pandas as pd\\nimport matplotlib.pyplot as plt\\nimport seaborn as sns"]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
'''
            },
            {
                "path": "requirements.txt",
                "content": '''scikit-learn>=1.3.0
pandas>=2.0.0
numpy>=1.24.0
mlflow>=2.8.0
matplotlib>=3.7.0
seaborn>=0.12.0
joblib>=1.3.0
jupyter>=1.0.0
'''
            },
            {
                "path": ".gitignore",
                "content": '''__pycache__/
*.pyc
.env
venv/
data/raw/
data/processed/
models/
mlruns/
.ipynb_checkpoints/
'''
            },
            {
                "path": "data/.gitkeep",
                "content": ""
            },
            {
                "path": "models/.gitkeep",
                "content": ""
            }
        ]
    },
    
    # 6. Microservice Template
    {
        "name": "Python Microservice",
        "description": "Docker-ready microservice with FastAPI, Redis caching, and health checks",
        "category": "microservice",
        "language": "python",
        "framework": "fastapi",
        "tags": ["microservice", "docker", "redis", "fastapi", "kubernetes"],
        "version": "1.0.0",
        "dependencies": {
            "python": ">=3.9",
            "packages": [
                "fastapi>=0.100.0",
                "uvicorn>=0.22.0",
                "redis>=4.5.0",
                "httpx>=0.24.0",
                "prometheus-client>=0.17.0",
                "structlog>=23.1.0"
            ]
        },
        "scripts": {
            "dev": "uvicorn app.main:app --reload --port 8000",
            "start": "uvicorn app.main:app --host 0.0.0.0 --port 8000",
            "docker-build": "docker build -t my-service .",
            "docker-run": "docker run -p 8000:8000 my-service"
        },
        "files": [
            {
                "path": "app/main.py",
                "content": '''"""Microservice Entry Point"""
from fastapi import FastAPI
from prometheus_client import make_asgi_app
import structlog

from app.api import router
from app.health import health_router
from app.middleware import setup_middleware

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)

logger = structlog.get_logger()

app = FastAPI(
    title="Microservice",
    version="1.0.0",
    docs_url="/docs"
)

# Setup middleware
setup_middleware(app)

# Mount prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include routers
app.include_router(health_router)
app.include_router(router, prefix="/api/v1")

@app.on_event("startup")
async def startup():
    logger.info("service_starting")

@app.on_event("shutdown")
async def shutdown():
    logger.info("service_stopping")
'''
            },
            {
                "path": "app/api/__init__.py",
                "content": '''"""API Routes"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def root():
    return {"service": "running"}
'''
            },
            {
                "path": "app/health.py",
                "content": '''"""Health Check Endpoints"""
from fastapi import APIRouter
import redis
import os

health_router = APIRouter(tags=["Health"])

@health_router.get("/health")
async def health():
    return {"status": "healthy"}

@health_router.get("/ready")
async def readiness():
    checks = {"database": True, "cache": check_redis()}
    all_healthy = all(checks.values())
    return {"ready": all_healthy, "checks": checks}

def check_redis() -> bool:
    try:
        r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"))
        r.ping()
        return True
    except:
        return False
'''
            },
            {
                "path": "app/middleware.py",
                "content": '''"""Middleware Configuration"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        logger.info("request", method=request.method, path=request.url.path, 
                   status=response.status_code, duration_ms=round(duration*1000))
        return response

def setup_middleware(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LoggingMiddleware)
'''
            },
            {
                "path": "Dockerfile",
                "content": '''FROM python:3.11-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''
            },
            {
                "path": "docker-compose.yml",
                "content": '''version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
'''
            },
            {
                "path": "k8s/deployment.yaml",
                "content": '''apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-service
  template:
    metadata:
      labels:
        app: my-service
    spec:
      containers:
      - name: my-service
        image: my-service:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
'''
            },
            {
                "path": "requirements.txt",
                "content": '''fastapi>=0.100.0
uvicorn>=0.22.0
redis>=4.5.0
httpx>=0.24.0
prometheus-client>=0.17.0
structlog>=23.1.0
'''
            },
            {
                "path": ".gitignore",
                "content": '''__pycache__/
.env
venv/
'''
            }
        ]
    }
]


class ProjectTemplatesService:
    """Service for managing project templates"""
    
    def __init__(self, db_session: AsyncSession = None):
        self.db = db_session
        self.templates = BUILT_IN_TEMPLATES
    
    async def seed_templates(self, db: AsyncSession):
        """Seed built-in templates to database"""
        from app.database.models_extended import ProjectTemplate
        
        for template_data in BUILT_IN_TEMPLATES:
            existing = await db.execute(
                select(ProjectTemplate).where(
                    ProjectTemplate.name == template_data["name"],
                    ProjectTemplate.is_built_in == True
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            template = ProjectTemplate(
                name=template_data["name"],
                description=template_data["description"],
                category=template_data["category"],
                language=template_data["language"],
                framework=template_data.get("framework"),
                tags=template_data.get("tags", []),
                files=template_data["files"],
                dependencies=template_data.get("dependencies"),
                scripts=template_data.get("scripts"),
                version=template_data.get("version", "1.0.0"),
                is_built_in=True,
                is_active=True
            )
            db.add(template)
        
        await db.commit()
        logger.info(f"Seeded {len(BUILT_IN_TEMPLATES)} project templates")
    
    async def list_templates(
        self, 
        db: AsyncSession,
        category: Optional[str] = None,
        language: Optional[str] = None,
        framework: Optional[str] = None
    ) -> List[Dict]:
        """List available templates with optional filtering"""
        from app.database.models_extended import ProjectTemplate
        
        query = select(ProjectTemplate).where(ProjectTemplate.is_active == True)
        
        if category:
            query = query.where(ProjectTemplate.category == category)
        if language:
            query = query.where(ProjectTemplate.language == language)
        if framework:
            query = query.where(ProjectTemplate.framework == framework)
        
        result = await db.execute(query)
        templates = result.scalars().all()
        
        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "language": t.language,
                "framework": t.framework,
                "tags": t.tags,
                "version": t.version,
                "usage_count": t.usage_count,
                "rating": t.rating,
                "is_built_in": t.is_built_in,
                "thumbnail_url": t.thumbnail_url
            }
            for t in templates
        ]
    
    async def get_template(self, db: AsyncSession, template_id: str) -> Optional[Dict]:
        """Get a specific template by ID"""
        from app.database.models_extended import ProjectTemplate
        
        result = await db.execute(
            select(ProjectTemplate).where(ProjectTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        
        if not template:
            return None
        
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "language": template.language,
            "framework": template.framework,
            "tags": template.tags,
            "files": template.files,
            "dependencies": template.dependencies,
            "scripts": template.scripts,
            "env_template": template.env_template,
            "readme_template": template.readme_template,
            "version": template.version
        }
    
    async def create_project_from_template(
        self,
        db: AsyncSession,
        template_id: str,
        project_name: str,
        project_description: Optional[str] = None,
        customizations: Optional[Dict] = None
    ) -> Dict:
        """Create a new project from a template"""
        from app.database.models_extended import ProjectTemplate
        from app.database.models import Project, File
        
        # Get template
        result = await db.execute(
            select(ProjectTemplate).where(ProjectTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # Create project
        project = Project(
            name=project_name,
            description=project_description or template.description,
            framework=template.framework,
            status="active"
        )
        db.add(project)
        await db.flush()
        
        # Create files from template
        created_files = []
        for file_data in template.files:
            content = file_data["content"]
            
            # Apply customizations
            if customizations:
                for key, value in customizations.items():
                    content = content.replace(f"{{{{ {key} }}}}", str(value))
            
            file = File(
                project_id=project.id,
                path=file_data["path"],
                content=content,
                language=self._detect_language(file_data["path"])
            )
            db.add(file)
            created_files.append(file_data["path"])
        
        # Generate README if not present
        if "README.md" not in [f["path"] for f in template.files]:
            readme = self._generate_readme(project_name, template, customizations)
            db.add(File(
                project_id=project.id,
                path="README.md",
                content=readme,
                language="markdown"
            ))
            created_files.append("README.md")
        
        # Update template usage count
        template.usage_count += 1
        
        await db.commit()
        
        return {
            "project_id": project.id,
            "name": project_name,
            "files_created": created_files,
            "template_used": template.name
        }
    
    def _detect_language(self, path: str) -> str:
        """Detect language from file extension"""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".css": "css",
            ".html": "html",
            ".sql": "sql",
            ".sh": "bash",
            ".dockerfile": "dockerfile"
        }
        _, ext = os.path.splitext(path.lower())
        if path.lower() == "dockerfile":
            return "dockerfile"
        return ext_map.get(ext, "text")
    
    def _generate_readme(
        self, 
        project_name: str, 
        template,
        customizations: Optional[Dict] = None
    ) -> str:
        """Generate a README.md for the project"""
        deps = template.dependencies or {}
        scripts = template.scripts or {}
        
        readme = f"""# {project_name}

{template.description}

## Quick Start

### Prerequisites

"""
        if "python" in deps:
            readme += f"- Python {deps['python']}\n"
        if "node" in deps:
            readme += f"- Node.js {deps['node']}\n"
        
        readme += """
### Installation

```bash
# Clone the repository
git clone <repository-url>
cd {project_name}

"""
        if template.language == "python":
            readme += """# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt
```

"""
        elif template.language in ["javascript", "typescript"]:
            readme += """# Install dependencies
npm install
```

"""
        
        if scripts:
            readme += "## Available Scripts\n\n"
            for name, cmd in scripts.items():
                readme += f"- **{name}**: `{cmd}`\n"
        
        readme += f"""

## Project Structure

This project was generated from the **{template.name}** template.

## License

MIT
"""
        return readme
    
    async def create_custom_template(
        self,
        db: AsyncSession,
        name: str,
        description: str,
        category: str,
        language: str,
        files: List[Dict],
        framework: Optional[str] = None,
        tags: Optional[List[str]] = None,
        dependencies: Optional[Dict] = None
    ) -> Dict:
        """Create a custom template"""
        from app.database.models_extended import ProjectTemplate
        
        template = ProjectTemplate(
            name=name,
            description=description,
            category=category,
            language=language,
            framework=framework,
            tags=tags or [],
            files=files,
            dependencies=dependencies,
            is_built_in=False,
            is_active=True
        )
        
        db.add(template)
        await db.commit()
        
        return {
            "id": template.id,
            "name": template.name,
            "message": "Template created successfully"
        }
