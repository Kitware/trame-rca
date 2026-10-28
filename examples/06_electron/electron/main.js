import { app, BrowserWindow } from 'electron/main';
import { fileURLToPath } from 'node:url';
import { launchTrame, webPreferences } from '@kitware/trame-rca-electron';

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
      fileURLToPath(new URL('../app.py', import.meta.url)),
      '--electron-versions',
      JSON.stringify({ electron, chrome, node, v8 }),
    ],
    onStats: (s) => console.log(`[renderer] ${s.view} frames=${s.frames} fps=${s.fps} ${s.info}`),
    onExit: () => app.quit(),
  });
});

app.on('window-all-closed', () => app.quit());
