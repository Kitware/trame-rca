import { useEffect, useMemo, useRef } from "react";

import { ImageStreamController } from "trame-rca-js";

import {
  type AnyProps,
  type ImageStreamContextValue,
  RcaImageStreamContext,
} from "../context";

export default function ImageStream(props: AnyProps) {
  const { name = "default", poolSize = 4, slot, children } = props;
  const propsRef = useRef<AnyProps>(props);
  propsRef.current = props;
  const controllerRef = useRef<ImageStreamController | null>(null);
  const ctx = useRef({
    image: null as HTMLImageElement | null,
    listeners: new Set<() => void>(),
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
    const controller = new ImageStreamController({
      source: propsRef.current,
      name,
      poolSize: propsRef.current.poolSize ?? 4,
      onImage: (img: HTMLImageElement) => {
        ctx.current.image = img;
        ctx.current.listeners.forEach((fn) => fn());
      },
    });
    controllerRef.current = controller;
    controller.mount();

    return () => {
      controller.unmount();
      controllerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name]);

  useEffect(() => {
    const controller = controllerRef.current;
    if (!controller) return;
    controller.poolSize = poolSize;
    controller.updatePoolSize();
  }, [poolSize]);

  return (
    <RcaImageStreamContext.Provider value={contextValue}>
      {slot ? slot() : children}
    </RcaImageStreamContext.Provider>
  );
}
