/**
 * Device pixel ratio, guarded for non-browser environments (tests, SSR).
 */
export function getDevicePixelRatio() {
  if (typeof window === 'undefined') {
    return 1;
  }
  return Math.max(1, window.devicePixelRatio);
}
