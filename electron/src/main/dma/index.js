// Each module loads its platform's libraries when imported: pidfd.js needs Linux's libc,
// iosurface.js needs macOS frameworks, winhandle.js needs kernel32. So import only this
// platform's, and asynchronously: a top-level await would stop CommonJS apps from
// require()-ing this package.
export const loadDma = (platform) => {
  if (platform === 'darwin') return import('./iosurface.js');
  if (platform === 'win32') return import('./winhandle.js');
  return import('./pidfd.js');
};
