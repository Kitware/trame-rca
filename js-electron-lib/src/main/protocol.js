// The texture channel between the Electron main process (EMP) and trame-rca, as
// newline-delimited JSON on 127.0.0.1. See trame_rca/electron/comm.py for the messages.
// Nothing in here touches Electron or the OS, so it can be tested with plain node.

import { randomBytes, timingSafeEqual } from 'node:crypto';

// Must match trame_rca.electron.comm.PROTOCOL_VERSION.
const PROTOCOL_VERSION = 1;

// The environment variable the trame server finds its token in. Must match
// trame_rca.electron.comm.TOKEN_ENV.
const TOKEN_ENV = 'TRAME_ELECTRON_TOKEN';

// A peer that hasn't sent its auth message by then, or sends more than this before it, is dropped.
const AUTH_TIMEOUT_MS = 5000;
const MAX_AUTH_BYTES = 4096;

const newToken = () => randomBytes(32).toString('hex');

// Whether `msg` is the auth message carrying `token`: the first thing trame must send.
const checkAuth = (msg, token) => {
  if (msg?.type !== 'auth' || typeof msg.token !== 'string') return false;
  const got = Buffer.from(msg.token);
  const want = Buffer.from(token);
  return got.length === want.length && timingSafeEqual(got, want);
};

// The texture passport trame-rca should share its texture with, for this platform.
// On Linux, Electron uses Wayland when it's available, unless --ozone-platform=x11.
const passportName = ({ platform, ozonePlatform, ozonePlatformHint, waylandDisplay }) => {
  if (platform === 'darwin') return 'iosurface';
  if (platform === 'win32') return 'nthandle';
  // --ozone-platform wins over --ozone-platform-hint, whose default is auto.
  const ozone = ozonePlatform || ozonePlatformHint || 'auto';
  const wayland = ozone === 'auto' ? !!waylandDisplay : ozone === 'wayland';
  return wayland ? 'wayland-dmabuf' : 'x11-dmabuf';
};

// `refreshRate` is the refresh rate in Hz of the display showing the window: trame-rca's
// default frame rate. Left out when Electron doesn't know it.
const helloMessage = (passport, refreshRate) => ({
  type: 'hello',
  protocol: PROTOCOL_VERSION,
  passport,
  ...(refreshRate > 0 ? { refresh_rate: refreshRate } : {}),
});

const checkProtocol = (msg) => {
  if (msg.protocol !== PROTOCOL_VERSION) {
    throw new Error(
      `trame-rca speaks shared texture protocol ${msg.protocol}, trame-rca-electron speaks ` +
        `${PROTOCOL_VERSION}: update trame-rca or trame-rca-electron so they match`,
    );
  }
};

// Calls onMessage with every complete JSON line fed in, and onBadLine with lines that
// aren't JSON instead of throwing out of the socket's data handler.
const createLineParser = (onMessage, onBadLine) => {
  let buf = '';
  return (chunk) => {
    buf += chunk.toString();
    let nl;
    while ((nl = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, nl);
      buf = buf.slice(nl + 1);
      let msg;
      try {
        msg = JSON.parse(line);
      } catch (err) {
        onBadLine?.(line, err);
        continue;
      }
      onMessage(msg);
    }
  };
};

const encode = (msg) => JSON.stringify(msg) + '\n';

// Which OS handle a texture message carries.
const handleKind = (msg) => {
  if (msg.ioSurfaceId !== undefined) return 'ioSurface';
  if (msg.ntHandle !== undefined) return 'ntHandle';
  return 'nativePixmap';
};

// The nativePixmap handle of a dma-buf texture, once its fds are duplicated into this process.
const nativePixmap = (msg, localFds) => ({
  nativePixmap: {
    planes: msg.planes.map((p, i) => ({
      fd: localFds[i],
      stride: p.stride,
      offset: p.offset,
      size: p.size,
    })),
    modifier: msg.modifier,
    supportsZeroCopyWebGpuImport: false,
  },
});

// The textureInfo of sharedTexture.importSharedTexture, for a texture message and its handle.
const textureInfo = (msg, handle) => ({
  pixelFormat: msg.pixelFormat,
  codedSize: { width: msg.width, height: msg.height },
  visibleRect: { x: 0, y: 0, width: msg.width, height: msg.height },
  handle,
});

export {
  AUTH_TIMEOUT_MS,
  MAX_AUTH_BYTES,
  PROTOCOL_VERSION,
  TOKEN_ENV,
  checkAuth,
  checkProtocol,
  createLineParser,
  encode,
  handleKind,
  helloMessage,
  nativePixmap,
  newToken,
  passportName,
  textureInfo,
};
