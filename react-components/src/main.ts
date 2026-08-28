import type { ComponentType } from "react";

import "./style.css";

import DisplayArea from "./components/DisplayArea";
import ImageDisplayArea from "./components/ImageDisplayArea";
import ImageRegion from "./components/ImageRegion";
import ImageStream from "./components/ImageStream";
import MediaSourceDisplayArea from "./components/MediaSourceDisplayArea";
import RawImageDisplayArea from "./components/RawImageDisplayArea";
import RemoteControlledArea from "./components/RemoteControlledArea";
import StatisticsDisplay from "./components/StatisticsDisplay";
import VideoDecoderDisplayArea from "./components/VideoDecoderDisplayArea";

// tags match the trame_rca Python widgets
const COMPONENTS: Record<string, ComponentType<any>> = {
  "display-area": DisplayArea,
  "image-display-area": ImageDisplayArea,
  "image-region": ImageRegion,
  "image-stream": ImageStream,
  "media-source-display-area": MediaSourceDisplayArea,
  "raw-image-display-area": RawImageDisplayArea,
  "remote-controlled-area": RemoteControlledArea,
  "statistics-display": StatisticsDisplay,
  "video-decoder-display-area": VideoDecoderDisplayArea,
};

interface Registry {
  register(tag: string, component: ComponentType<any>): void;
}

export function install(registerTag: Registry["register"]) {
  Object.entries(COMPONENTS).forEach(([tag, component]) => {
    registerTag(tag, component);
  });
}
