const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const os = require('os');
const fs = require('fs');
const http = require('http');

let mainWindow;
let backendProcess;
const isDev = !app.isPackaged;

function getBackendPath() {
  if (isDev) {
    return path.join(__dirname, '..', 'backend', 'main.py');
  }
  // Packed app: backend is in resources/app/backend/
  const resourcesPath = app.getPath('resources');
  return path.join(resourcesPath, 'app', 'backend', 'main.py');
}

function startBackend() {
  const backendPath = getBackendPath();
  const isExe = backendPath.endsWith('.exe');
  
  const env = { ...process.env, USE_SQLITE: 'true' };
  
  if (isExe) {
    backendProcess = spawn(backendPath, [], { 
      env, 
      stdio: isDev ? 'inherit' : 'ignore',
    });
  } else {
    const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
    backendProcess = spawn(pythonPath, [backendPath], { 
      env, 
      stdio: isDev ? 'inherit' : 'ignore',
    });
  }

  backendProcess.on('error', (err) => console.error('[Backend Error]', err));
  backendProcess.on('close', (code) => console.log(`[Backend exited ${code}]`));
}

function startFrontend() {
  if (isDev) {
    // In dev mode, start Next.js dev server on port 3000
    const frontendDir = path.join(__dirname, '..', 'frontend');
    const nextDev = spawn('npx', ['next', 'dev', '-p', '3000'], {
      cwd: frontendDir,
      stdio: 'inherit',
    });
    return nextDev;
  } else {
    // In packed mode, no need to start a separate frontend server
    // The app loads the static HTML directly
    return null;
  }
}

async function waitForBackend() {
  const maxRetries = 25;
  for (let i = 0; i < maxRetries; i++) {
    try {
      await new Promise((resolve, reject) => {
        const req = http.get('http://localhost:8000/health', { timeout: 500 }, (res) => {
          if (res.statusCode === 200) resolve();
          else reject(new Error('Not ready'));
        });
        req.on('error', reject);
        req.on('timeout', () => { req.destroy(); reject(new Error('Timeout')); });
      });
      return true;
    } catch {
      await new Promise(r => setTimeout(r, 400));
    }
  }
  return false;
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: 'CodeForge AI',
    backgroundColor: '#020617',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools();
  } else {
    const indexPath = path.join(app.getPath('resources'), 'app', 'frontend', 'index.html');
    mainWindow.loadFile(indexPath);
  }

  mainWindow.on('closed', () => { mainWindow = null; });
}

app.whenReady().then(async () => {
  startBackend();
  
  const ready = await waitForBackend();
  if (!ready) {
    console.warn('[WARN] Backend did not respond in time');
  }
  
  startFrontend();
  await new Promise(r => setTimeout(r, 2000));
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (mainWindow === null) createWindow();
});

app.on('will-quit', () => {
  if (backendProcess) backendProcess.kill();
});

ipcMain.handle('get-app-info', () => ({
  version: app.getVersion(),
  platform: os.platform(),
  arch: os.arch(),
}));

ipcMain.handle('open-external', (event, url) => {
  shell.openExternal(url);
});

ipcMain.handle('get-backend-status', () => ({
  running: backendProcess && backendProcess.exitCode === null,
}));
