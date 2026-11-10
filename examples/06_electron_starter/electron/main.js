import { app, BrowserWindow } from 'electron/main';
import { fileURLToPath } from 'node:url';
import { launchTrame, webPreferences } from '@kitware/trame-rca-electron';

// Run ../app.py with the python of the active environment, unless PYTHON says otherwise.
const python = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');

app.whenReady().then(() => {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    useContentSize: true,
    webPreferences: webPreferences(),
  });
  launchTrame(win, {
    command: python,
    args: [fileURLToPath(new URL('../app.py', import.meta.url))],
    onExit: () => app.quit(),
  });
});

app.on('window-all-closed', () => app.quit());
