// Open another process's IOSurface by its global ID with IOSurfaceLookup.
// Only works for surfaces created with kIOSurfaceIsGlobal (deprecated, unsandboxed only).
const koffi = require('koffi');

const iosurface = koffi.load('/System/Library/Frameworks/IOSurface.framework/IOSurface');
const cf = koffi.load('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation');

const IOSurfaceRef = koffi.pointer('IOSurfaceRef', koffi.opaque());
const IOSurfaceLookup = iosurface.func('IOSurfaceLookup', IOSurfaceRef, ['uint32_t']);
const IOSurfaceGetWidth = iosurface.func('IOSurfaceGetWidth', 'size_t', [IOSurfaceRef]);
const IOSurfaceGetHeight = iosurface.func('IOSurfaceGetHeight', 'size_t', [IOSurfaceRef]);
const IOSurfaceGetPixelFormat = iosurface.func('IOSurfaceGetPixelFormat', 'uint32_t', [IOSurfaceRef]);
const CFRelease = cf.func('CFRelease', 'void', [IOSurfaceRef]);

const fourccStr = (code) => String.fromCharCode((code >>> 24) & 0xff, (code >>> 16) & 0xff, (code >>> 8) & 0xff, code & 0xff);

// Returns a retained IOSurfaceRef; release it with releaseSurface().
const lookupSurface = (id) => {
  const ref = IOSurfaceLookup(id);
  if (!ref) throw new Error(`IOSurfaceLookup(${id}) failed (not global, or already freed)`);
  return ref;
};

const describeSurface = (ref) =>
  `${IOSurfaceGetWidth(ref)}x${IOSurfaceGetHeight(ref)} ${fourccStr(IOSurfaceGetPixelFormat(ref))}`;

// sharedTexture wants the IOSurfaceRef pointer value in a Buffer.
const surfaceHandle = (ref) => {
  const buf = Buffer.alloc(8);
  buf.writeBigUInt64LE(BigInt(koffi.address(ref)));
  return buf;
};

const releaseSurface = (ref) => CFRelease(ref);

module.exports = { lookupSurface, describeSurface, surfaceHandle, releaseSurface };
