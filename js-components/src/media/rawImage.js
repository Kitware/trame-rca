/**
 * Renders a raw RGB24 / RGBA32 streamed payload onto a canvas.
 *
 * @returns {Promise<boolean>} true when the payload was handled, false when
 *   the type is not a supported raw image format.
 */
export async function drawRawImage(canvas, meta, content) {
  const ctx = canvas.getContext('2d');

  if (meta.type.includes('image/rgb24')) {
    const data = content.buffer
      ? content
      : new Uint8Array(await content.arrayBuffer());
    canvas.width = meta.w;
    canvas.height = meta.h;
    const imageData = ctx.createImageData(meta.w, meta.h);
    const pixels = imageData.data;
    let iRGB = 0;
    let iRGBA = 0;
    while (iRGBA < pixels.length) {
      pixels[iRGBA++] = data[iRGB++];
      pixels[iRGBA++] = data[iRGB++];
      pixels[iRGBA++] = data[iRGB++];
      pixels[iRGBA++] = 255;
    }
    ctx.putImageData(imageData, 0, 0);
    return true;
  }

  if (meta.type.includes('image/rgba32')) {
    const data = new Uint8ClampedArray(
      content.buffer ? content : await content.arrayBuffer()
    );
    canvas.width = meta.w;
    canvas.height = meta.h;
    const imageData = new ImageData(data, meta.w, meta.h);
    ctx.putImageData(imageData, 0, 0);
    return true;
  }

  return false;
}
