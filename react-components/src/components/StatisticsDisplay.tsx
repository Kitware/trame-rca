import { useEffect, useRef, useState } from "react";

import { sizeUnit, StatisticsDisplayController } from "trame-rca-js";

import { type AnyProps } from "../context";

export default function StatisticsDisplay(props: AnyProps) {
  const {
    name = "default",
    fpsDelta = 4,
    statWindowSize = 10,
    historyWindowSize = 255,
    resetMsThreshold = 1000,
    wsLinkTopic = "trame.rca.topic.stream",
  } = props;
  const propsRef = useRef<AnyProps>(props);
  propsRef.current = props;
  const rootElem = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const controllerRef = useRef<StatisticsDisplayController | null>(null);
  const [avg, setAvg] = useState(30);
  const [totalSize, setTotalSize] = useState(0);

  useEffect(() => {
    const controller = new StatisticsDisplayController({
      source: propsRef.current,
      name,
      fpsDelta: propsRef.current.fpsDelta ?? 4,
      statWindowSize: propsRef.current.statWindowSize ?? 10,
      historyWindowSize: propsRef.current.historyWindowSize ?? 255,
      resetMsThreshold: propsRef.current.resetMsThreshold ?? 1000,
      wsLinkTopic: propsRef.current.wsLinkTopic ?? "trame.rca.topic.stream",
      packetDecorator: propsRef.current.packetDecorator,
      onStats: ({ avg: nextAvg, totalSize: nextTotalSize }: any) => {
        setAvg(nextAvg);
        setTotalSize(nextTotalSize);
      },
      onResize: ({ cw, ch }: any) => {
        const canvas = canvasRef.current;
        if (canvas) {
          canvas.width = cw;
          canvas.height = ch;
        }
      },
    });
    controllerRef.current = controller;
    controller.mount({
      root: rootElem.current,
      canvas: canvasRef.current,
    });

    return () => {
      controller.unmount();
      controllerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name, wsLinkTopic]);

  useEffect(() => {
    controllerRef.current?.setStatWindowSize(statWindowSize);
  }, [statWindowSize]);
  useEffect(() => {
    controllerRef.current?.setHistoryWindowSize(historyWindowSize);
  }, [historyWindowSize]);
  useEffect(() => {
    controllerRef.current?.setResetMsThreshold(resetMsThreshold);
  }, [resetMsThreshold]);
  useEffect(() => {
    controllerRef.current?.setFpsDelta(fpsDelta);
  }, [fpsDelta]);

  return (
    <div
      ref={rootElem}
      style={{ width: "100%", height: "100%", position: "relative" }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          zIndex: 1,
          display: "flex",
          justifyContent: "space-around",
          fontSize: "0.875rem",
          fontWeight: 500,
        }}
      >
        <div>{avg.toFixed(1)} fps</div>
        <div>{sizeUnit(totalSize)}</div>
      </div>
      <canvas
        ref={canvasRef}
        className="js-canvas"
        style={{ position: "absolute", left: 0, top: 0 }}
      />
    </div>
  );
}
