const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const rootDir = path.resolve(__dirname, '../..');
const frontendDir = path.join(rootDir, 'frontend');
const backendDir = path.join(rootDir, 'backend');
const electronDir = path.join(rootDir, 'electron');
const appDir = path.join(electronDir, 'app');

console.log('========================================');
console.log('CodeForge AI - Build');
console.log('========================================\n');

async function run(cmd, cwd) {
  console.log(`> ${cmd}`);
  try {
    execSync(cmd, { cwd, stdio: 'inherit' });
  } catch (err) {
    console.error(`\nFailed: ${cmd}`);
    process.exit(1);
  }
}

async function buildFrontend() {
  console.log('\n=== Step 1: Build Next.js frontend ===');
  await run('npm run build', frontendDir);
  console.log('Frontend built successfully');
}

async function prepareBackend() {
  console.log('\n=== Step 2: Prepare backend ===');
  
  // Create app directory structure
  if (fs.existsSync(appDir)) {
    fs.rmSync(appDir, { recursive: true });
  }
  fs.mkdirSync(path.join(appDir, 'backend'), { recursive: true });
  fs.mkdirSync(path.join(appDir, 'frontend'), { recursive: true });
  
  // Copy backend files
  function copyDir(src, dest) {
    fs.mkdirSync(dest, { recursive: true });
    const entries = fs.readdirSync(src, { withFileTypes: true });
    for (const entry of entries) {
      const srcPath = path.join(src, entry.name);
      const destPath = path.join(dest, entry.name);
      if (entry.isDirectory()) {
        copyDir(srcPath, destPath);
      } else {
        fs.copyFileSync(srcPath, destPath);
      }
    }
  }
  
  copyDir(backendDir, path.join(appDir, 'backend'));
  
  // Remove __pycache__, .pyc, venv, db files
  function cleanDir(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (entry.name === '__pycache__' || entry.name === 'venv' || entry.name === '.venv') {
          fs.rmSync(full, { recursive: true });
        } else {
          cleanDir(full);
        }
      } else if (entry.name.endsWith('.pyc') || entry.name.endsWith('.db-wal') || entry.name.endsWith('.db-shm')) {
        fs.unlinkSync(full);
      }
    }
  }
  cleanDir(path.join(appDir, 'backend'));

  // Copy frontend build output
  const frontendOutDir = path.join(frontendDir, 'out');
  if (fs.existsSync(frontendOutDir)) {
    fs.cpSync(frontendOutDir, path.join(appDir, 'frontend'), { recursive: true });
    console.log('Frontend bundled to app/frontend');
  }
  
  console.log('Backend prepared');
}

async function packageApp(platform) {
  console.log('\n=== Step 3: Packaging Electron app ===');
  
  const cmd = platform === 'win32'
    ? 'npx electron-builder --win --x64'
    : platform === 'darwin'
      ? 'npx electron-builder --mac --x64'
      : 'npx electron-builder --linux --x64';
  
  await run(cmd, electronDir);
}

async function main() {
  const targetPlatform = process.argv[2] || 'win32';
  
  await buildFrontend();
  await prepareBackend();
  await packageApp(targetPlatform);
  
  console.log('\n========================================');
  console.log('Build complete!');
  console.log('Output directory: electron/dist');
  console.log('========================================');
}

main().catch(err => {
  console.error('Build failed:', err);
  process.exit(1);
});
