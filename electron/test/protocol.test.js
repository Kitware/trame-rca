import test from 'node:test';
import assert from 'node:assert/strict';

import * as protocol from '../src/main/protocol.js';

test('passportName picks the platform passport', () => {
  assert.equal(protocol.passportName({ platform: 'darwin' }), 'iosurface');
  assert.equal(protocol.passportName({ platform: 'win32' }), 'nthandle');
});

test('passportName follows ozone switches and WAYLAND_DISPLAY on linux', () => {
  const linux = (o) => protocol.passportName({ platform: 'linux', ...o });
  assert.equal(linux({ waylandDisplay: 'wayland-0' }), 'wayland-dmabuf');
  assert.equal(linux({}), 'x11-dmabuf');
  assert.equal(linux({ ozonePlatform: 'x11', waylandDisplay: 'wayland-0' }), 'x11-dmabuf');
  assert.equal(linux({ ozonePlatformHint: 'wayland' }), 'wayland-dmabuf');
  // --ozone-platform should win over the --ozone-platform-hint.
  assert.equal(linux({ ozonePlatform: 'x11', ozonePlatformHint: 'wayland' }), 'x11-dmabuf');
});

test('hello carries the protocol version', () => {
  assert.deepEqual(protocol.helloMessage('iosurface'), {
    type: 'hello',
    protocol: protocol.PROTOCOL_VERSION,
    passport: 'iosurface',
  });
});

test('checkProtocol rejects other versions', () => {
  protocol.checkProtocol({ protocol: protocol.PROTOCOL_VERSION });
  assert.throws(() => protocol.checkProtocol({ protocol: protocol.PROTOCOL_VERSION + 1 }), /protocol/);
  assert.throws(() => protocol.checkProtocol({}), /protocol/);
});

test('line parser joins chunks and reports bad lines', () => {
  const messages = [];
  const bad = [];
  const feed = protocol.createLineParser(
    (m) => messages.push(m),
    (line) => bad.push(line),
  );
  feed('{"type":"fr');
  feed('ame","seq":1}\n{oops}\n{"type":"frame","seq":2}\n{"type"');
  assert.deepEqual(messages, [
    { type: 'frame', seq: 1 },
    { type: 'frame', seq: 2 },
  ]);
  assert.deepEqual(bad, ['{oops}']);
  feed(':"frame","seq":3}\n');
  assert.equal(messages.length, 3);
});

test('handleKind and textureInfo', () => {
  assert.equal(protocol.handleKind({ ioSurfaceId: 3 }), 'ioSurface');
  assert.equal(protocol.handleKind({ ntHandle: 4 }), 'ntHandle');
  assert.equal(protocol.handleKind({ planes: [] }), 'nativePixmap');
  const msg = { pixelFormat: 'bgra', width: 4, height: 2 };
  assert.deepEqual(protocol.textureInfo(msg, { h: 1 }), {
    pixelFormat: 'bgra',
    codedSize: { width: 4, height: 2 },
    visibleRect: { x: 0, y: 0, width: 4, height: 2 },
    handle: { h: 1 },
  });
});

test('nativePixmap swaps in the local fds', () => {
  const msg = {
    modifier: '0',
    planes: [{ fd: 30, stride: 16, offset: 0, size: 64 }],
  };
  assert.deepEqual(protocol.nativePixmap(msg, [7]), {
    nativePixmap: {
      planes: [{ fd: 7, stride: 16, offset: 0, size: 64 }],
      modifier: '0',
      supportsZeroCopyWebGpuImport: false,
    },
  });
});
