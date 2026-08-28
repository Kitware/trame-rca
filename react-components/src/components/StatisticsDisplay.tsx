import { useEffect, useRef, useState } from "react";

import { type AnyProps, getSession } from "../context";
import { FPSMonitor } from "../utils/FPSMonitor";

const UNITS = ["B/s", "KB/s", "MB/s"];

function sizeUnit(v: number) {
  let value = v;
  for (let i = 0; i < 3; i++) {
    if (value < 1000) {
      return `${value.toFixed(1)} ${UNITS[i]}`;
    }
    value /= 1000;
  }
  return `${value.toFixed(1)} GB/s`;
}

const DEFAULT_PACKET_DECORATOR = ({ name, meta, content }: any) => ({
  name,
  serverTime: meta.st,
  contentSize: content.length,
});

export default function StatisticsDisplay(props: AnyProps) {
  const {
    name = "default",
    fpsDelta = 4,
    statWindowSize = 10,
    historyWindowSize = 255,
    resetMsThreshold = 255,
    wsLinkTopic = "trame.rca.topic.stream",
  } = props;
  const propsRef = useRef<AnyProps>(props);
  propsRef.current = props;
  const rootElem = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const sizeRef = useRef({ cw: 200, ch: 200 });
  const ctx = useRef<any>(null);
  const [avg, setAvg] = useState(30);
  const [totalSize, setTotalSize] = useState(0);

  useEffect(() => {
    const context: any = {
      monitor: new FPSMonitor(
        propsRef.current.historyWindowSize ?? 255,
        propsRef.current.statWindowSize ?? 10,
      ),
    };
    ctx.current = context;

    function draw(
      client: number[],
      server: number[],
      clientColor = "#1DE9B688",
      serverColor = "#EF9A9A",
    ) {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const { cw: width, ch: height } = sizeRef.current;
      const c2d = canvas.getContext("2d") as CanvasRenderingContext2D;
      const delta = propsRef.current.fpsDelta ?? 4;

      const centerHeight = Math.floor(height * 0.5 + 0.5);
      const yScale = centerHeight / (1001 * delta);
      const xScale = width / (client.length - 2);

      c2d.clearRect(0, 0, width, height);

      // ref
      c2d.strokeStyle = "black";
      c2d.beginPath();
      c2d.moveTo(0, centerHeight);
      c2d.lineTo(width, centerHeight);
      c2d.stroke();
      c2d.strokeStyle = "#eee";
      for (let i = 0; i < delta; i++) {
        c2d.beginPath();
        c2d.moveTo(0, centerHeight + 1000 * (i + 1) * yScale);
        c2d.lineTo(width, centerHeight + 1000 * (i + 1) * yScale);
        c2d.stroke();
        c2d.beginPath();
        c2d.moveTo(0, centerHeight - 1000 * (i + 1) * yScale);
        c2d.lineTo(width, centerHeight - 1000 * (i + 1) * yScale);
        c2d.stroke();
      }

      // client
      c2d.strokeStyle = clientColor;
      c2d.lineWidth = 8;
      c2d.beginPath();
      c2d.moveTo(0, centerHeight - yScale * client[1]);
      for (let i = 2; i < client.length; i++) {
        c2d.lineTo((i - 1) * xScale, centerHeight - yScale * client[i]);
      }
      c2d.stroke();

      // server
      c2d.strokeStyle = serverColor;
      c2d.lineWidth = 2;
      c2d.beginPath();
      c2d.moveTo(0, centerHeight - yScale * server[1]);
      for (let i = 2; i < server.length; i++) {
        c2d.lineTo((i - 1) * xScale, centerHeight - yScale * server[i]);
      }
      c2d.stroke();
    }

    const onStreamPacket = ([v]: any[]) => {
      const decorate =
        propsRef.current.packetDecorator || DEFAULT_PACKET_DECORATOR;
      const { name: streamName, serverTime, contentSize } = decorate(v);
      if (propsRef.current.name !== streamName) return;
      const stats = context.monitor.addEntry(serverTime, contentSize);
      if (stats) {
        setAvg(stats.avgFps);
        setTotalSize(stats.totalSize);
        draw(stats.client, stats.server);
      }
    };

    const session = getSession(propsRef.current);
    const subscription = session?.subscribe(
      propsRef.current.wsLinkTopic ?? "trame.rca.topic.stream",
      onStreamPacket,
    );

    const observer = new ResizeObserver(() => {
      if (!rootElem.current) return;
      const { width, height } = rootElem.current.getBoundingClientRect();
      sizeRef.current = { cw: width, ch: height };
      const canvas = canvasRef.current;
      if (canvas) {
        canvas.width = width;
        canvas.height = height;
      }
    });
    observer.observe(rootElem.current as HTMLDivElement);

    return () => {
      observer.disconnect();
      if (subscription) session?.unsubscribe(subscription);
      ctx.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name, wsLinkTopic]);

  // prop-driven monitor tuning
  useEffect(() => {
    if (ctx.current) ctx.current.monitor.windowStatSize = statWindowSize;
  }, [statWindowSize]);
  useEffect(() => {
    if (ctx.current) ctx.current.monitor.windowSize = historyWindowSize;
  }, [historyWindowSize]);
  useEffect(() => {
    if (ctx.current)
      ctx.current.monitor.newInteractionThreshold = resetMsThreshold;
  }, [resetMsThreshold]);
  void fpsDelta;

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
