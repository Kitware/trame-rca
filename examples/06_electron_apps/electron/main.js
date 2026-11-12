import { app, BrowserWindow } from 'electron/main';
import { fileURLToPath } from 'node:url';
import { launchTrame, webPreferences } from '@kitware/trame-rca-electron';

// Run ../app.py with the python of the active environment, unless PYTHON says otherwise.
const python = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const trame_app_name = process.env.TRAME_APP_NAME || "starter"

// Forward the arguments after `npm start --` e.g. --points 500000.
const appArgs = process.argv.slice(app.isPackaged ? 1 : 2);

app.whenReady().then(() => {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    useContentSize: true,
    webPreferences: webPreferences(),
  });
  launchTrame(win, {
    command: python,
    args: [fileURLToPath(new URL(`../app_${trame_app_name}.py`, import.meta.url)), ...appArgs],
    onExit: () => app.quit(),
    // onStats: (s) => console.log(`[renderer] ${s.view} frames=${s.frames} fps=${s.fps} ${s.info}`),
  });
});

app.on('window-all-closed', () => app.quit());
