import { createContext } from "react";

// React equivalents of the vue provide/inject keys used across components.
// The trame session access itself lives in `trame-rca-js` (`getTrame`/`getSession`)
// and is used by the shared controllers.

export type PushSizeFn = (addOn?: Record<string, unknown>) => void;

// RemoteControlledArea -> MediaSourceDisplayArea (rcaPushSize)
export const RcaPushSizeContext = createContext<PushSizeFn | null>(null);

// ImageStream -> ImageRegion (rcaImageStream / rcaImageStreamName)
export interface ImageStreamContextValue {
  name: string;
  // returns the latest decoded frame; subscribe notifies on new frames
  getImage: () => HTMLImageElement | null;
  subscribe: (listener: () => void) => () => void;
}
export const RcaImageStreamContext =
  createContext<ImageStreamContextValue | null>(null);

export type AnyProps = Record<string, any>;
