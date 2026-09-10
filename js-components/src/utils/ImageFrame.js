/**
 * Decodes a streamed image payload into an <img> element via an object URL.
 *
 * One instance is reused in a small pool to keep decode smooth. `update`
 * returns `false` while a previous load is still pending so callers can skip
 * frames instead of queueing them.
 */
export class ImageFrame {
  constructor(onLoad) {
    this.onLoad = onLoad;
    this.img = new Image();
    this.pending = false;
    this.url = '';
    this.blob = null;
    this.img.addEventListener('error', () => {
      this.pending = false;
    });
    this.img.addEventListener('load', () => {
      this.pending = false;
      this.onLoad?.(this.img, this.url);
    });
  }

  update(type, content) {
    if (this.pending) {
      return false;
    }
    this.pending = true;
    window.URL.revokeObjectURL(this.url);
    this.blob = new Blob([content], { type });
    this.url = URL.createObjectURL(this.blob);
    this.img.src = this.url;
    return true;
  }
}
