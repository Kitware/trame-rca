// Draws the frames the main process sends into the page's shared-texture-display-areas.
// Use it as a BrowserWindow's preload (see webPreferences()), or import it from yours.
import { contextBridge, ipcRenderer, sharedTexture } from 'electron';

const STATS_INTERVAL_MS = 1000;

// The canvas of each shared-texture-display-area, by view name, attached when the component
// mounts.
const views = new Map();

// The main process sends the view's name along with every frame.
sharedTexture.setSharedTextureReceiver(async ({ importedSharedTexture }, view) => {
  const target = views.get(view);
  if (!target) {
    importedSharedTexture.release();
    return;
  }
  const { canvas, ctx } = target;
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
  target.info = `${vf.codedWidth}x${vf.codedHeight} ${vf.format}`;
  vf.close();
  importedSharedTexture.release();
  target.frames++;
  target.windowFrames++;
});

// Frames are rendered on demand, so report stats over a timed interval.
setInterval(() => {
  const now = performance.now();
  views.forEach((target, view) => {
    const fps = (target.windowFrames * 1000) / (now - target.windowStart);
    const hadFrames = target.windowFrames > 0;
    target.windowStart = now;
    target.windowFrames = 0;
    const { frames, info } = target;
    target.onStats?.({ fps: Number(fps.toFixed(1)), frames, info });
    if (hadFrames) {
      ipcRenderer.send('trame-rca:stats', { view, frames, fps: fps.toFixed(1), info });
    }
  });
}, STATS_INTERVAL_MS);

// The page's world can't touch sharedTexture or VideoFrames from here, but it can hand us its
// canvases, and a callback for their frame rate.
contextBridge.exposeInMainWorld('trameRcaSharedTexture', {
  attach: (view, el, statsCallback) => {
    views.set(view, {
      canvas: el,
      ctx: el.getContext('2d'),
      onStats: statsCallback ?? null,
      frames: 0,
      windowStart: performance.now(),
      windowFrames: 0,
      info: '',
    });
  },
  detach: (view, el) => {
    if (views.get(view)?.canvas === el) views.delete(view);
  },
});
