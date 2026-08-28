import { useEffect, useRef, useState } from "react";

import { type AnyProps, getSession } from "../context";

export default function RawImageDisplayArea(props: AnyProps) {
  const { name = "default", imageStyle = { width: "100%" } } = props;
  const propsRef = useRef<AnyProps>(props);
  propsRef.current = props;
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [hasContent, setHasContent] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current as HTMLCanvasElement;
    const ctx = canvas.getContext("2d") as CanvasRenderingContext2D;

    const onImage = async ([{ name: streamName, meta, content }]: any[]) => {
      if (propsRef.current.name !== streamName) return;
      if (meta.type.includes("image/rgb24")) {
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
        setHasContent(true);
      } else if (meta.type.includes("image/rgba32")) {
        const data = new Uint8ClampedArray(
          content.buffer ? content : await content.arrayBuffer(),
        );
        canvas.width = meta.w;
        canvas.height = meta.h;
        const imageData = new ImageData(data, meta.w, meta.h);
        ctx.putImageData(imageData, 0, 0);
        setHasContent(true);
      } else {
        setHasContent(false);
      }
    };

    const session = getSession(propsRef.current);
    const subscription = session?.subscribe("trame.rca.topic.stream", onImage);
    return () => {
      if (subscription) session?.unsubscribe(subscription);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name]);

  return (
    <canvas
      ref={canvasRef}
      className="raw-image-display-area js-canvas"
      style={{
        ...(imageStyle || {}),
        display: hasContent ? undefined : "none",
      }}
    />
  );
}
