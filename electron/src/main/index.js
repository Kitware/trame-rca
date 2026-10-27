import { app, ipcMain, sharedTexture } from 'electron/main';
import { spawn } from 'node:child_process';
import net from 'node:net';
import { fileURLToPath } from 'node:url';

import { loadDma } from './dma/index.js';
import * as protocol from './protocol.js';

// The preload a BrowserWindow needs to show shared-texture views. Electron only runs
// ES module preloads with the .mjs extension.
const preloadPath = fileURLToPath(new URL('../preload.mjs', import.meta.url));

// The webPreferences a BrowserWindow needs to show shared-texture views.
const webPreferences = (extra = {}) => ({
  preload: preloadPath,
  // The preload needs electron's sharedTexture, and ES module preloads can't be sandboxed.
  sandbox: false,
  ...extra,
});

// Holds this process's reference to one of the producer's textures. `dma` is this
// platform's module from loadDma().
class TextureHandle {
  constructor(msg, dma, log) {
    this.dma = dma;
    this.localFds = [];
    this.surfaceRef = null;
    this.localHandle = null;
    this.info = protocol.textureInfo(msg, this._open(msg, log));
  }

  _open(msg, log) {
    const kind = protocol.handleKind(msg);
    if (kind === 'ioSurface') {
      // Open the producer's global IOSurface in this process.
      const { lookupSurface, describeSurface, surfaceHandle } = this.dma;
      this.surfaceRef = lookupSurface(msg.ioSurfaceId);
      log.info(
        `[trame-rca] texture ${msg.width}x${msg.height} (${msg.pixelFormat}) IOSurface id=${msg.ioSurfaceId} ${describeSurface(this.surfaceRef)}`,
      );
      return { ioSurface: surfaceHandle(this.surfaceRef) };
    }
    if (kind === 'ntHandle') {
      // Duplicate the producer's NT handle into this process.
      const { dupHandleFromProcess, handleBuffer } = this.dma;
      this.localHandle = dupHandleFromProcess(msg.pid, msg.ntHandle);
      log.info(
        `[trame-rca] texture ${msg.width}x${msg.height} (${msg.pixelFormat}) handle 0x${msg.ntHandle.toString(16)} -> 0x${this.localHandle.toString(16)}`,
      );
      return { ntHandle: handleBuffer(this.localHandle) };
    }
    // Duplicate the producer's dma-buf fds into this process.
    this.localFds = msg.planes.map((p) => this.dma.dupFdFromProcess(msg.pid, p.fd));
    log.info(
      `[trame-rca] texture ${msg.width}x${msg.height} ${msg.fourcc} (${msg.pixelFormat}) modifier=${msg.modifier} fds ${msg.planes.map((p) => p.fd)} -> ${this.localFds}`,
    );
    return protocol.nativePixmap(msg, this.localFds);
  }

  release() {
    this.localFds.forEach((fd) => this.dma.closeFd(fd));
    this.localFds = [];
    if (this.surfaceRef) this.dma.releaseSurface(this.surfaceRef);
    this.surfaceRef = null;
    if (this.localHandle) this.dma.closeHandle(this.localHandle);
    this.localHandle = null;
  }
}

// Spawn the trame server and load its page in `win` once it is ready. The page's
// shared-texture views then show the texture the server renders into.
//
// `command` is the executable to run (a python interpreter, a frozen backend, ...) and
// `args` its arguments, e.g. ['app.py'].
// trame-rca-electron appends the arguments the server needs: --server --port 0 --emp-port <port>.
//
// Returns { process, close }. close() kills the server and releases the textures; it is
// called on its own when `win` closes.
const launchTrame = (
  win,
  { command, args = [], cwd, env, onExit, onStats, log = console },
) => {
  if (!command) throw new Error('launchTrame: `command` is required');
  let socket = null;
  // The producer's ring of textures, by slot.
  let textures = [];
  // This platform's dma module, loaded before the server is spawned.
  let dma = null;
  let closed = false;
  const result = { process: null, close: null };

  const send = (msg) => {
    if (socket && !socket.destroyed) socket.write(protocol.encode(msg));
  };

  const releaseTextures = (fromSlot = 0) => {
    textures.slice(fromSlot).forEach((t) => t?.release());
    textures = textures.slice(0, fromSlot);
  };

  const forwardFrame = async (info, msg) => {
    // Once per frame: a frame that failed to transfer may still be released late by the renderer.
    let done = false;
    const frameDone = () => {
      if (done) return;
      done = true;
      send({ type: 'frame_done', seq: msg.seq });
    };
    const frameDropped = () => {
      if (done) return;
      done = true;
      send({ type: 'frame_done', seq: msg.seq, dropped: true });
    };
    let imported = null;
    try {
      // Electron retains the texture's handle, so it can be re-imported every frame.
      imported = sharedTexture.importSharedTexture({
        textureInfo: { ...info, timestamp: msg.timestamp_us },
        allReferencesReleased: frameDone,
      });
      await sharedTexture.sendSharedTexture({
        frame: win.webContents.mainFrame,
        importedSharedTexture: imported,
      });
    } catch (err) {
      // sendSharedTexture uses a 1000ms timeout. If the ERP is still busy loading the page,
      // or if some other error occurred, the page would never have shown this frame, so ask
      // for it again.
      log.warn(`[trame-rca] frame ${msg.seq} dropped: ${err.message}`);
      frameDropped();
    } finally {
      imported?.release();
    }
  };

  const onMessage = (conn) => (msg) => {
    if (msg.type === 'server_ready') {
      try {
        protocol.checkProtocol(msg);
      } catch (err) {
        log.error(`[trame-rca] ${err.message}`);
        conn.destroy();
        return;
      }
      log.info(`[trame-rca] loading ${msg.url}`);
      win.loadURL(msg.url);
    } else if (msg.type === 'texture') {
      try {
        const { slot, slots } = msg;
        textures[slot]?.release();
        textures[slot] = new TextureHandle(msg, dma, log);
        // release textures beyond `slots` to handle shrink
	releaseTextures(slots);
      } catch (err) {
        log.error('[trame-rca] failed to open the texture:', err);
        conn.destroy();
      }
    } else if (msg.type === 'frame') {
      const texture = textures[msg.slot];
      if (texture) forwardFrame(texture.info, msg);
    }
  };

  const handleConnection = (conn) => {
    if (socket) {
      // One server per window: ignore anything else knocking.
      conn.destroy();
      return;
    }
    socket = conn;
    // Without this, Nagle holds frame_done back until the producer's delayed ACK.
    conn.setNoDelay(true);
    send(
      protocol.helloMessage(
        protocol.passportName({
          platform: process.platform,
          ozonePlatform: app.commandLine.getSwitchValue('ozone-platform'),
          ozonePlatformHint: app.commandLine.getSwitchValue('ozone-platform-hint'),
          waylandDisplay: process.env.WAYLAND_DISPLAY,
        }),
      ),
    );
    conn.on(
      'data',
      protocol.createLineParser(onMessage(conn), (line, err) =>
        log.error(
          `[trame-rca] bad line from trame (${line.length} chars): ${JSON.stringify(line)}`,
          err,
        ),
      ),
    );
    conn.on('close', () => log.info('[trame-rca] trame disconnected'));
  };

  const statsListener = (event, stats) => {
    if (event.sender === win.webContents) onStats?.(stats);
  };
  ipcMain.on('trame-rca:stats', statsListener);

  const server = net.createServer(handleConnection);

  result.close = () => {
    if (closed) return;
    closed = true;
    ipcMain.off('trame-rca:stats', statsListener);
    result.process?.kill();
    socket?.destroy();
    socket = null;
    server.close();
    releaseTextures();
  };
  win.once('closed', result.close);

  server.listen(0, '127.0.0.1', async () => {
    try {
      dma = await loadDma(process.platform);
    } catch (err) {
      log.error('[trame-rca] failed to load the OS texture API:', err);
      result.close();
      return;
    }
    if (closed) return;
    const { port } = server.address();
    const fullArgs = [...args, '--server', '--port', '0', '--emp-port', String(port)];
    log.info(`[trame-rca] spawning ${command} ${fullArgs.join(' ')}`);
    result.process = spawn(command, fullArgs, {
      cwd,
      env: env ?? process.env,
      stdio: ['ignore', 'inherit', 'inherit'],
    });
    result.process.on('exit', (code, signal) => {
      log.info(`[trame-rca] trame exited code=${code} signal=${signal}`);
      onExit?.(code, signal);
    });
  });

  return result;
};

export { launchTrame, preloadPath, webPreferences, protocol };
