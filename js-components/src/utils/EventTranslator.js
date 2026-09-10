/**
 * Translates normalized screen events to coordinates within a sub-region of
 * the full streamed image.
 */
export class EventTranslator {
  constructor() {
    this.fullWidth = 300;
    this.fullHeight = 300;
    this.xOffset = 0;
    this.yOffset = 0;
    this.xSize = 300;
    this.ySize = 300;
  }

  translate(event) {
    const out = { ...event };
    if (event.x !== undefined) {
      out.x = Math.round(this.xOffset + this.xSize * (event.x / event.w));
      out.y = Math.round(this.yOffset + this.ySize * (event.y / event.h));
      out.w = this.fullWidth;
      out.h = this.fullHeight;
    }
    return out;
  }
}
