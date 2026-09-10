import { useEffect, useRef } from "react";

import { RemoteControlledAreaController } from "trame-rca-js";

import { type AnyProps, RcaPushSizeContext } from "../context";

import DisplayArea from "./DisplayArea";

export default function RemoteControlledArea(props: AnyProps) {
  const {
    name = "default",
    origin = "anonymous",
    display = "image",
    sendMouseMove = false,
    eventThrottleMs = 25,
    resizeThrottleMs = 100,
    imageStyle = { width: "100%" },
    monitor = 0,
    onStats,
    slot,
  } = props;
  const propsRef = useRef<AnyProps>(props);
  propsRef.current = props;
  const rootElem = useRef<HTMLDivElement | null>(null);
  const controllerRef = useRef<RemoteControlledAreaController | null>(null);

  useEffect(() => {
    const controller = new RemoteControlledAreaController({
      source: propsRef.current,
      name,
      origin,
      sendMouseMove,
      eventThrottleMs,
      resizeThrottleMs,
    });
    controllerRef.current = controller;
    controller.mount(rootElem.current);

    return () => {
      controller.unmount();
      controllerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name]);

  // prop-driven updates
  useEffect(() => {
    controllerRef.current?.setResizeThrottleMs(resizeThrottleMs);
  }, [resizeThrottleMs]);
  useEffect(() => {
    controllerRef.current?.setEventThrottleMs(eventThrottleMs);
  }, [eventThrottleMs]);
  useEffect(() => {
    controllerRef.current?.setSendMouseMove(sendMouseMove);
  }, [sendMouseMove]);
  useEffect(() => {
    controllerRef.current?.setName(name);
  }, [name]);
  useEffect(() => {
    controllerRef.current?.setOrigin(origin);
  }, [origin]);

  return (
    <div className="remote-controlled-area" ref={rootElem}>
      <div className="remote-controlled-area-content">
        <RcaPushSizeContext.Provider
          value={(addOn) => controllerRef.current?.pushSize(addOn)}
        >
          <DisplayArea
            key={name}
            display={display}
            imageStyle={imageStyle}
            name={name}
            origin={origin}
            monitor={monitor}
            onStats={onStats}
            trame={props.trame}
          />
          {slot ? slot() : null}
        </RcaPushSizeContext.Provider>
      </div>
    </div>
  );
}
