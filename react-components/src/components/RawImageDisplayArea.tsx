import { useEffect, useRef, useState } from "react";

import { RawImageDisplayAreaController } from "trame-rca-js";

import { type AnyProps } from "../context";

export default function RawImageDisplayArea(props: AnyProps) {
  const { name = "default", imageStyle = { width: "100%" } } = props;
  const propsRef = useRef<AnyProps>(props);
  propsRef.current = props;
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [hasContent, setHasContent] = useState(false);
  const controllerRef = useRef<RawImageDisplayAreaController | null>(null);

  useEffect(() => {
    const controller = new RawImageDisplayAreaController({
      source: propsRef.current,
      name,
      onHasContent: (value: boolean) => setHasContent(value),
    });
    controllerRef.current = controller;
    controller.mount(canvasRef.current);

    return () => {
      controller.unmount();
      controllerRef.current = null;
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
