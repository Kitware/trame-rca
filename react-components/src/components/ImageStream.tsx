import { useEffect, useMemo, useRef } from "react";

import {
  type AnyProps,
  getSession,
  type ImageStreamContextValue,
  RcaImageStreamContext,
} from "../context";

class ImageFrame {
  img: HTMLImageElement;
  url = "";
  blob: Blob | null = null;

  constructor(onLoad: (img: HTMLImageElement) => void) {
    this.img = new Image();
    this.img.addEventListener("load", () => {
      onLoad(this.img);
    });
  }

  update(type: string, content: BlobPart) {
    window.URL.revokeObjectURL(this.url);
    this.blob = new Blob([content], { type });
    this.url = URL.createObjectURL(this.blob);
    this.img.src = this.url;
  }
}

export default function ImageStream(props: AnyProps) {
  const { name = "default", poolSize = 4, slot } = props;
  const propsRef = useRef<AnyProps>(props);
  propsRef.current = props;
  const ctx = useRef<any>({
    image: null,
    listeners: new Set<() => void>(),
    frames: [] as ImageFrame[],
    nextFrameIndex: 0,
  });

  const contextValue = useMemo<ImageStreamContextValue>(
    () => ({
      name,
      getImage: () => ctx.current.image,
      subscribe: (listener: () => void) => {
        ctx.current.listeners.add(listener);
        return () => ctx.current?.listeners.delete(listener);
      },
    }),
    [name],
  );

  useEffect(() => {
    const context = ctx.current;
    const onLoad = (img: HTMLImageElement) => {
      context.image = img;
      context.listeners.forEach((fn: () => void) => fn());
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
    context.updatePoolSize();

    function nextFrame() {
      context.nextFrameIndex =
        (context.nextFrameIndex + 1) % context.frames.length;
      return context.frames[context.nextFrameIndex];
    }

    const onImage = ([{ name: streamName, meta, content }]: any[]) => {
      if (propsRef.current.name === streamName) {
        nextFrame().update(meta.type, content);
      }
    };

    const session = getSession(propsRef.current);
    const subscription = session?.subscribe("trame.rca.topic.stream", onImage);
    return () => {
      if (subscription) session?.unsubscribe(subscription);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name]);

  useEffect(() => {
    ctx.current?.updatePoolSize?.();
  }, [poolSize]);

  return (
    <RcaImageStreamContext.Provider value={contextValue}>
      {slot ? slot() : null}
    </RcaImageStreamContext.Provider>
  );
}
