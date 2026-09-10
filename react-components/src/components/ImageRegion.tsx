import { useContext, useEffect, useRef } from "react";

import { ImageRegionController } from "trame-rca-js";

import { type AnyProps, RcaImageStreamContext } from "../context";

export default function ImageRegion(props: AnyProps) {
  const {
    bounds,
    enableInteraction = false,
    sendMouseMove = false,
    sendMouseClick = false,
    eventThrottleMs = 25,
  } = props;
  const propsRef = useRef<AnyProps>(props);
  propsRef.current = props;
  const rootElem = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const stream = useContext(RcaImageStreamContext);
  const streamRef = useRef(stream);
  streamRef.current = stream;
  const controllerRef = useRef<ImageRegionController | null>(null);

  // one-time construction
  useEffect(() => {
    const controller = new ImageRegionController({
      source: propsRef.current,
      name: streamRef.current?.name,
      bounds: propsRef.current.bounds,
      enableInteraction: propsRef.current.enableInteraction ?? false,
      sendMouseMove: propsRef.current.sendMouseMove ?? false,
      sendMouseClick: propsRef.current.sendMouseClick ?? false,
      eventThrottleMs: propsRef.current.eventThrottleMs ?? 25,
      getImage: () => streamRef.current?.getImage(),
      onSize: (event: Record<string, unknown>) =>
        propsRef.current.onSize?.(event),
    });
    controllerRef.current = controller;
    controller.mount({ root: rootElem.current, canvas: canvasRef.current });

    return () => {
      controller.unmount();
      controllerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // redraw when the bounds change
  useEffect(() => {
    controllerRef.current?.setBounds(propsRef.current.bounds);
  }, [bounds]);

  // redraw when a new frame arrives
  useEffect(() => {
    if (!stream) return undefined;
    const draw = () => controllerRef.current?.draw();
    draw();
    return stream.subscribe(draw);
  }, [stream, bounds]);

  // prop-driven updates
  useEffect(() => {
    controllerRef.current?.setEnableInteraction(enableInteraction);
  }, [enableInteraction]);
  useEffect(() => {
    controllerRef.current?.setSendMouseMove(sendMouseMove);
  }, [sendMouseMove]);
  useEffect(() => {
    controllerRef.current?.setSendMouseClick(sendMouseClick);
  }, [sendMouseClick]);
  useEffect(() => {
    controllerRef.current?.setEventThrottleMs(eventThrottleMs);
  }, [eventThrottleMs]);

  return (
    <div className="image-region" ref={rootElem}>
      <canvas className="image-region-canvas" ref={canvasRef} />
    </div>
  );
}
