import { type AnyProps } from "../context";
import ImageDisplayArea from "./ImageDisplayArea";
import MediaSourceDisplayArea from "./MediaSourceDisplayArea";
import RawImageDisplayArea from "./RawImageDisplayArea";
import VideoDecoderDisplayArea from "./VideoDecoderDisplayArea";

export default function DisplayArea(props: AnyProps) {
  const {
    name = "default",
    origin = "anonymous",
    display = "image",
    imageStyle = { width: "100%" },
    monitor = 0,
    onStats,
    trame,
  } = props;
  return (
    <div className="display-area">
      {display === "image" ? (
        <ImageDisplayArea
          name={name}
          origin={origin}
          poolSize={4}
          imageStyle={imageStyle}
          monitor={monitor}
          onStats={onStats}
          trame={trame}
        />
      ) : null}
      {display === "media-source" ? (
        <MediaSourceDisplayArea name={name} origin={origin} trame={trame} />
      ) : null}
      {display === "video-decoder" ? (
        <VideoDecoderDisplayArea name={name} origin={origin} trame={trame} />
      ) : null}
      {display === "raw-image" ? (
        <RawImageDisplayArea
          name={name}
          origin={origin}
          imageStyle={imageStyle}
          trame={trame}
        />
      ) : null}
    </div>
  );
}
