const { app, BrowserWindow } = require('electron/main');
const path = require('node:path');
const { launchTrame, webPreferences } = require('@kitware/trame-rca-electron');

// Run ../app.py with the python of the active environment, unless PYTHON says otherwise.
const python = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');

app.whenReady().then(() => {
  const win = new BrowserWindow({
    width: 1920,
    height: 1080,
    useContentSize: true,
    webPreferences: webPreferences(),
  });
  const { electron, chrome, node, v8 } = process.versions;
  launchTrame(win, {
    command: python,
    args: [
      path.join(__dirname, '..', 'app.py'),
      '--electron-versions',
      JSON.stringify({ electron, chrome, node, v8 }),
    ],
    onStats: (s) => console.log(`[renderer] frames=${s.frames} fps=${s.fps} ${s.info}`),
    onExit: () => app.quit(),
  });
});

app.on('window-all-closed', () => app.quit());
