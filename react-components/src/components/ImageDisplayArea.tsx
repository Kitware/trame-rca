import { useEffect, useRef, useState } from "react";

import { type AnyProps, getSession } from "../context";
import { FPSMonitor } from "../utils/FPSMonitor";

const SUPPORTED_IMAGE_TYPES: Record<string, number> = {
  "image/apng": 1,
  "image/avif": 1,
  "image/gif": 1,
  "image/jpeg": 1,
  "image/png": 1,
  "image/svg+xml": 1,
  "image/webp": 1,
};

class ImageFrame {
  img: HTMLImageElement;
  pending = false;
  url = "";
  blob: Blob | null = null;

  constructor(onLoad: (url: string) => void) {
    this.img = new Image();
    this.img.addEventListener("error", () => {
      this.pending = false;
    });
    this.img.addEventListener("load", () => {
      this.pending = false;
      onLoad(this.url);
    });
  }

  update(type: string, content: BlobPart) {
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

export default function ImageDisplayArea(props: AnyProps) {
  const {
    name = "default",
    poolSize = 4,
    imageStyle = { width: "100%" },
    monitor = 0,
  } = props;
  const propsRef = useRef<AnyProps>(props);
  propsRef.current = props;

  const [displayURL, setDisplayURL] = useState("");
  const [hasContent, setHasContent] = useState(false);
  const ctx = useRef<any>(null);

  useEffect(() => {
    const context: any = {
      fpsMonitor: new FPSMonitor(10, 10),
      frames: [] as ImageFrame[],
      nextFrameIndex: 0,
    };
    ctx.current = context;

    const onLoad = (url: string) => {
      setDisplayURL(url);
      setHasContent(true);
    };
    context.updatePoolSize = () => {
      const size = propsRef.current.poolSize ?? 4;
      while (context.frames.length < size) {
        context.frames.push(new ImageFrame(onLoad));
      }
      while (context.frames.length > size) {
        context.frames.pop();
      }
    };
    context.updateMonitorWindow = () => {
      const bufferSize = Math.max(10, propsRef.current.monitor ?? 0);
      context.fpsMonitor.windowSize = bufferSize;
      context.fpsMonitor.windowStatSize = bufferSize;
    };
    context.updatePoolSize();

    const session = getSession(propsRef.current);
    const onImage = ([{ name: streamName, meta, content }]: any[]) => {
      if (propsRef.current.name !== streamName) return;
      if (SUPPORTED_IMAGE_TYPES[meta.type]) {
        const nextIdx = (context.nextFrameIndex + 1) % context.frames.length;
        const frame = context.frames[nextIdx];
        if (frame.update(meta.type, content)) {
          context.nextFrameIndex = nextIdx;
          if (propsRef.current.monitor) {
            const serverTime = meta.st;
            const contentSize = content.length;
            const stats = context.fpsMonitor.addEntry(serverTime, contentSize);
            if (stats) {
              const { avgFps, totalSize } = stats;
              propsRef.current.onStats?.({
                fps: Math.round(avgFps),
                bps: Math.floor(totalSize),
                st: serverTime,
              });
            }
          }
        }
      } else {
        setHasContent(false);
      }
    };
    const subscription = session?.subscribe("trame.rca.topic.stream", onImage);

    return () => {
      if (subscription) session?.unsubscribe(subscription);
      ctx.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name]);

  useEffect(() => {
    ctx.current?.updatePoolSize?.();
  }, [poolSize]);
  useEffect(() => {
    ctx.current?.updateMonitorWindow?.();
  }, [monitor]);

  return (
    <img
      className="image-display-area"
      style={{
        ...(imageStyle || {}),
        display: hasContent ? undefined : "none",
      }}
      src={displayURL}
      draggable={false}
    />
  );
}
