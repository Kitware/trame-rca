import { useContext, useEffect, useRef, useState } from "react";

import { MediaSourceDisplayAreaController } from "trame-rca-js";

import { type AnyProps, RcaPushSizeContext } from "../context";

export default function MediaSourceDisplayArea(props: AnyProps) {
  const { name = "default" } = props;
  const propsRef = useRef<AnyProps>(props);
  propsRef.current = props;
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [hasContent, setHasContent] = useState(false);
  const pushSize = useContext(RcaPushSizeContext);
  const pushSizeRef = useRef(pushSize);
  pushSizeRef.current = pushSize;
  const controllerRef = useRef<MediaSourceDisplayAreaController | null>(null);

  useEffect(() => {
    const controller = new MediaSourceDisplayAreaController({
      source: propsRef.current,
      name,
      onHasContent: (value: boolean) => setHasContent(value),
      onPushSize: (addOn: Record<string, unknown>) =>
        pushSizeRef.current?.(addOn),
    });
    controllerRef.current = controller;
    controller.mount(videoRef.current);

    return () => {
      controller.unmount();
      controllerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name]);

  return (
    <video
      ref={videoRef}
      className="media-source-display-area"
      autoPlay
      muted
      style={{ display: hasContent ? undefined : "none" }}
    >
      Your browser does not support the video tag.
    </video>
  );
}
