import { useEffect, useRef, useState } from "react";

import { type AnyProps, getSession } from "../context";
import { DecoderWorker } from "../utils/decoder";

export default function VideoDecoderDisplayArea(props: AnyProps) {
  const { name = "default" } = props;
  const propsRef = useRef<AnyProps>(props);
  propsRef.current = props;
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isSupported] = useState(() => "VideoFrame" in window);

  useEffect(() => {
    const worker = new DecoderWorker();
    let subscription: unknown = null;
    const session = getSession(propsRef.current);

    if (isSupported) {
      worker.bindCanvas(canvasRef.current);

      const onChunkAvailable = async ([
        { name: streamName, meta, content },
      ]: any[]) => {
        // when we do not get octet-stream or valid codec, terminate worker.
        if (
          !meta.type.includes("application/octet-stream") ||
          !meta.codec.length ||
          meta.codec.includes("unknown")
        ) {
          return;
        }

        if (propsRef.current.name === streamName && meta.codec.length) {
          worker.setContentType(meta.codec, meta.w, meta.h);
          const data = content.buffer
            ? content
            : new Uint8Array(await content.arrayBuffer());
          worker.pushChunk(meta.st, meta.key, data);
        }
      };

      if (session) {
        session.call("trame.rca.reset", [propsRef.current.name]);
        subscription = session.subscribe(
          "trame.rca.topic.stream",
          onChunkAvailable,
        );
      }
    }

    return () => {
      worker.terminate();
      if (subscription) session?.unsubscribe(subscription);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name, isSupported]);

  return (
    <div className="video-decoder-display-area">
      {!isSupported ? <h1>WebCodecs API is not supported.</h1> : null}
      <canvas ref={canvasRef} className="js-canvas" />
    </div>
  );
}
