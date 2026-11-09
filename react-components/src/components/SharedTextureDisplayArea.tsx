import { useEffect, useRef } from "react";

import { type AnyProps } from "../context";

interface SharedTextureBridge {
  attach(
    view: string,
    canvas: HTMLCanvasElement,
    onStats?: (stats: unknown) => void,
  ): void;
  detach(view: string, canvas: HTMLCanvasElement): void;
}

declare global {
  interface Window {
    trameRcaSharedTexture?: SharedTextureBridge;
  }
}

// Shows the frames the trame-rca-electron preload draws from the texture VTK shares with
// Electron, for the view `name`. Only works in a page loaded by trame-rca-electron: the preload
// defines the bridge.
export default function SharedTextureDisplayArea(props: AnyProps) {
  const { name = "default" } = props;
  const propsRef = useRef<AnyProps>(props);
  propsRef.current = props;
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const bridge = window.trameRcaSharedTexture;
    if (!bridge) {
      console.warn(
        "shared-texture-display-area: no trameRcaSharedTexture bridge, not running in trame-rca-electron?",
      );
      return;
    }
    if (!canvas) return;
    bridge.attach(name, canvas, (stats) => propsRef.current.onStats?.(stats));
    return () => bridge.detach(name, canvas);
  }, [name]);

  return (
    <canvas
      ref={canvasRef}
      className="shared-texture-display-area"
      onContextMenu={(e) => e.preventDefault()}
    />
  );
}
