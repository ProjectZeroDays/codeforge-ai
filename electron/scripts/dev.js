const { spawn } = require('child_process');
const path = require('path');

const rootDir = path.resolve(__dirname, '../..');
const backendDir = path.join(rootDir, 'backend');
const frontendDir = path.join(rootDir, 'frontend');

console.log('Starting CodeForge AI in dev mode...\n');

// Start backend
const backendEnv = { ...process.env, USE_SQLITE: 'true' };
const backend = spawn('python', ['-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8000', '--log-level', 'info'], {
  cwd: backendDir,
  env: backendEnv,
  stdio: 'inherit',
});

// Start frontend after backend is ready
setTimeout(() => {
  const frontend = spawn('npx', ['next', 'start', '-p', '3000'], {
    cwd: frontendDir,
    stdio: 'inherit',
  });

  // Start electron
  const electron = spawn('npx', ['electron', '.'], {
    stdio: 'inherit',
  });
}, 3000);
