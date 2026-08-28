import { useContext, useEffect, useRef, useState } from "react";

import { type AnyProps, getSession, RcaPushSizeContext } from "../context";

class MseVideoDecoder {
  videoElement: HTMLVideoElement;
  mime: string;
  sourceBuffer: SourceBuffer | null = null;
  mediaSource: MediaSource | null = null;
  initSegment: Uint8Array | null = null;
  mediaSegments: Uint8Array[] = [];
  loaded = 0;

  constructor(
    videoElement: HTMLVideoElement,
    mime = "video/webm; codecs=vp09.00.10.08",
  ) {
    this.videoElement = videoElement;
    this.mime = mime;
    if ("MediaSource" in window) {
      this.mediaSource = new MediaSource();
      this.videoElement.src = URL.createObjectURL(this.mediaSource);
      // sourceopen -> append initSegment -> listen to updateend of source buffer.
      this.mediaSource.addEventListener("sourceopen", () => {
        if (MediaSource.isTypeSupported(this.mime)) {
          this.initSourceBuffer();
        } else {
          console.error(`Unsupported MIME type or codec: ${this.mime}`);
        }
      });
    } else {
      console.error("The Media Source Extensions API is not supported.");
    }
  }

  initSourceBuffer() {
    const mediaSource = this.mediaSource as MediaSource;
    this.sourceBuffer = mediaSource.addSourceBuffer(this.mime);
    this.sourceBuffer.mode = "sequence";
    if (this.initSegment) {
      this.sourceBuffer.appendBuffer(this.initSegment as BufferSource);
    } else {
      console.error("Need initialization segment");
    }
    this.sourceBuffer.onupdateend = () => {
      if (!this.mediaSegments.length) {
        return;
      } else if (this.sourceBuffer?.updating === false) {
        this.sourceBuffer.appendBuffer(
          this.mediaSegments.shift() as BufferSource,
        );
        this.loaded += 1;
      }
    };
  }

  queueChunk(data: Uint8Array) {
    if (
      this.mediaSource?.readyState === "open" &&
      this.sourceBuffer &&
      this.sourceBuffer.updating === false
    ) {
      this.sourceBuffer.appendBuffer(data as BufferSource);
      this.loaded += 1;
    } else {
      this.mediaSegments.push(data);
    }
  }

  exit() {
    this.sourceBuffer?.abort();
    this.mediaSource?.endOfStream();
    this.videoElement.play();
    URL.revokeObjectURL(this.videoElement.src);
  }
}

export default function MediaSourceDisplayArea(props: AnyProps) {
  const { name = "default" } = props;
  const propsRef = useRef<AnyProps>(props);
  propsRef.current = props;
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [hasContent, setHasContent] = useState(false);
  const pushSize = useContext(RcaPushSizeContext);
  const pushSizeRef = useRef(pushSize);
  pushSizeRef.current = pushSize;

  useEffect(() => {
    let decoder: MseVideoDecoder | null = null;

    const requestInitializationSegment = () => {
      pushSizeRef.current?.({ videoHeader: 1 });
    };

    const pushChunk = (bytes: Uint8Array, mime: string) => {
      const fourcc = Array.from(new Uint8Array(bytes).slice(0, 4))
        .map((byte) => byte.toString(16))
        .join("");
      if (fourcc == "1a45dfa3" && mime.includes("webm")) {
        console.log("detected ebml fourcc");
        if (decoder) {
          decoder.exit();
        }
        // create a video decoder with that video tag
        decoder = new MseVideoDecoder(videoRef.current as HTMLVideoElement);
        decoder.initSegment = new Uint8Array(bytes);
      } else if (decoder && decoder.mime !== mime) {
        console.log("detected mime change");
        requestInitializationSegment();
      } else if (decoder) {
        decoder.queueChunk(bytes);
        setHasContent(true);
      }
    };

    const onChunkAvailable = async ([
      { name: streamName, meta, content },
    ]: any[]) => {
      if (!meta.type.includes("video/")) {
        setHasContent(false);
        return;
      }
      if (propsRef.current.name === streamName) {
        const v = content.buffer
          ? content
          : new Uint8Array(await content.arrayBuffer());
        pushChunk(v, meta.type);
        setHasContent(true);
      }
    };

    const session = getSession(propsRef.current);
    const subscription = session?.subscribe(
      "trame.rca.topic.stream",
      onChunkAvailable,
    );
    if (session) {
      requestInitializationSegment();
    }

    return () => {
      if (subscription) {
        session?.unsubscribe(subscription);
        decoder?.exit();
      }
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
