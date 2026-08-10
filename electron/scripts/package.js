const { execSync } = require('child_process');
const path = require('path');

const rootDir = path.resolve(__dirname, '../..');
const electronDir = path.join(rootDir, 'electron');

const targetPlatform = process.argv[2] || 'win32';

console.log(`Packaging for ${targetPlatform}...`);

const commands = {
  win32: 'npx electron-builder --win --x64',
  darwin: 'npx electron-builder --mac --x64',
  linux: 'npx electron-builder --linux --x64',
};

const cmd = commands[targetPlatform];
if (!cmd) {
  console.error('Unknown platform:', targetPlatform);
  console.error('Supported: win32, darwin, linux');
  process.exit(1);
}

execSync(cmd, { cwd: electronDir, stdio: 'inherit' });
console.log('Done! Check the dist/ folder.');
