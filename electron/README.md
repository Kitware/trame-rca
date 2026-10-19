# @kitware/trame-rca-electron

Shows trame-rca `display="shared-texture"` views in Electron. The trame server renders VTK
into a GPU texture, and this package hands it to the page without encoding, or copying to the CPU.

This package and the `trame-rca` python package speak a versioned protocol (see
`src/main/protocol.js` and `trame_rca/electron/comm.py`): use matching releases.

## Use

```js
const { app, BrowserWindow } = require('electron/main');
const { launchTrame, webPreferences } = require('@kitware/trame-rca-electron');

app.whenReady().then(() => {
  const win = new BrowserWindow({ webPreferences: webPreferences() });
  launchTrame(win, { command: 'python3', args: ['app.py'], onExit: () => app.quit() });
});
```

`launchTrame(win, options)` spawns `command` with `args` plus `--server --port 0 --emp-port <port>`,
and loads the page in `win` once trame serves it. Options:

- `command`, `args`, `cwd`, `env`: the trame server to run. Any executable works: a python
  interpreter and a script, a frozen backend, etc.
- `onExit(code, signal)`: the server exited.
- `onStats({ fps, frames, info })`: once a second.
- `log`: defaults to `console`.

It returns `{ process, close }`. `close()` kills the server; it is called when `win` closes.

`webPreferences(extra)` sets the preload, and turns off the sandbox the preload needs for
`sharedTexture`. If the window needs its own preload, `require('@kitware/trame-rca-electron/preload')`
from it.

On the python side, see `examples/06_electron` in trame-rca.

## Packaging an app

Packaging (electron-builder or Forge, a frozen python backend, signing) belongs to each app.
What this package needs from a packaged app:

- `koffi` is a native module: unpack it from the asar archive (e.g. electron-builder's
  `asarUnpack: ["**/node_modules/koffi/**"]`).
- Pass the packaged backend as `command`. It must be spawned by `launchTrame`, as a direct child
  of the main process: on Linux, duplicating its dma-buf file descriptors needs ptrace access to
  it (`kernel.yama.ptrace_scope` at 1 or less).
- The frozen backend must include `vtkmodules` and the `serve` directories of `trame_rca` and of
  every other trame package it uses.
- macOS shares the texture as a global IOSurface, which does not work in an App Sandbox (so not on
  the Mac App Store).
- Linux: X11 is not supported yet, Electron must run under Wayland.
