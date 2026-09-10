import { useEffect, useRef, useState } from "react";

import { ImageDisplayAreaController } from "trame-rca-js";

import { type AnyProps } from "../context";

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
  const controllerRef = useRef<ImageDisplayAreaController | null>(null);

  useEffect(() => {
    const controller = new ImageDisplayAreaController({
      source: propsRef.current,
      name,
      poolSize: propsRef.current.poolSize ?? 4,
      monitor: propsRef.current.monitor ?? 0,
      onStats: (stats: any) => propsRef.current.onStats?.(stats),
      onDisplayUrl: (url: string) => setDisplayURL(url),
      onHasContent: (value: boolean) => setHasContent(value),
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

  useEffect(() => {
    const controller = controllerRef.current;
    if (!controller) return;
    controller.monitor = monitor;
    controller.updateMonitorWindow();
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
