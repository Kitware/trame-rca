import { app, BrowserWindow } from 'electron/main';
import { fileURLToPath } from 'node:url';
import { launchTrame, webPreferences } from '@kitware/trame-rca-electron';

// Run ../app.py with the python of the active environment, unless PYTHON says otherwise.
const python = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');

// Forward the arguments after `npm start --` to app.py, e.g. --points 500000.
const appArgs = process.argv.slice(app.isPackaged ? 1 : 2);

app.whenReady().then(() => {
  const win = new BrowserWindow({
    width: 1920,
    height: 1080,
    useContentSize: true,
    webPreferences: webPreferences(),
  });
  launchTrame(win, {
    command: python,
    args: [fileURLToPath(new URL('../app.py', import.meta.url)), ...appArgs],
    onStats: (s) => console.log(`[renderer] frames=${s.frames} fps=${s.fps} ${s.info}`),
    onExit: () => app.quit(),
  });
});

app.on('window-all-closed', () => app.quit());
