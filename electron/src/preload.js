// Draws the frames the main process sends into the page's shared-texture-display-area.
// Use it as a BrowserWindow's preload (see webPreferences()), or require it from yours.
const { contextBridge, ipcRenderer, sharedTexture } = require('electron');

const STATS_INTERVAL_MS = 1000;

// The canvas of the page's shared-texture-display-area, attached when the component mounts.
let canvas = null;
let ctx = null;
let onStats = null;

let frames = 0;
let windowStart = performance.now();
let windowFrames = 0;
let info = '';

sharedTexture.setSharedTextureReceiver(async ({ importedSharedTexture }) => {
  if (!canvas) {
    importedSharedTexture.release();
    return;
  }
  const vf = importedSharedTexture.getVideoFrame();
  // The canvas's pixels follow the producer's texture, which follows the canvas's size.
  if (canvas.width !== vf.displayWidth || canvas.height !== vf.displayHeight) {
    canvas.width = vf.displayWidth;
    canvas.height = vf.displayHeight;
  }
  // The producers render with GL, whose first row is the bottom, into textures whose first
  // row is the top: draw the frame upside down to undo that.
  ctx.setTransform(1, 0, 0, -1, 0, canvas.height);
  ctx.drawImage(vf, 0, 0, canvas.width, canvas.height);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  info = `${vf.codedWidth}x${vf.codedHeight} ${vf.format}`;
  vf.close();
  importedSharedTexture.release();
  frames++;
  windowFrames++;
});

// Frames are rendered on demand, so report stats over a timed interval.
setInterval(() => {
  const now = performance.now();
  const fps = (windowFrames * 1000) / (now - windowStart);
  const hadFrames = windowFrames > 0;
  windowStart = now;
  windowFrames = 0;
  onStats?.({ fps: Number(fps.toFixed(1)), frames, info });
  if (hadFrames && ctx) {
    ipcRenderer.send('trame-rca:stats', { frames, fps: fps.toFixed(1), info });
  }
}, STATS_INTERVAL_MS);

// The page's world can't touch sharedTexture or VideoFrames from here, but it can hand us its
// canvas, and a callback for the frame rate.
contextBridge.exposeInMainWorld('trameRcaSharedTexture', {
  attach: (el, statsCallback) => {
    canvas = el;
    ctx = el.getContext('2d');
    onStats = statsCallback ?? null;
  },
  detach: (el) => {
    if (canvas !== el) return;
    canvas = null;
    ctx = null;
    onStats = null;
  },
});
