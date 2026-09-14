import { useEffect, useRef, useState } from "react";

import { VideoDecoderDisplayAreaController } from "trame-rca-js";

import { type AnyProps } from "../context";

export default function VideoDecoderDisplayArea(props: AnyProps) {
  const { name = "default" } = props;
  const propsRef = useRef<AnyProps>(props);
  propsRef.current = props;
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isSupported, setIsSupported] = useState(() => "VideoFrame" in window);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<VideoDecoderDisplayAreaController | null>(null);

  useEffect(() => {
    const controller = new VideoDecoderDisplayAreaController({
      source: propsRef.current,
      name,
      onSupported: (value: boolean) => setIsSupported(value),
      onError: (message: string | null) => setError(message),
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
    <div className="video-decoder-display-area">
      {!isSupported ? <h1>WebCodecs API is not supported.</h1> : null}
      {isSupported && error ? <h1>{error}</h1> : null}
      <canvas ref={canvasRef} className="js-canvas" />
    </div>
  );
}
