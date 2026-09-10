import { FPSMonitor } from '../utils/FPSMonitor.js';
import { sizeUnit as formatSizeUnit } from '../utils/sizeUnit.js';
import { getSession, subscribe, unsubscribe } from '../session.js';

const DEFAULT_PACKET_DECORATOR = ({ name, meta, content }) => ({
  name,
  serverTime: meta.st,
  contentSize: content.length,
});

/**
 * Logic for the statistics display: fps/bandwidth monitor
 * subscription and canvas plotting.
 */
export class StatisticsDisplayController {
  constructor({
    source,
    name = 'default',
    fpsDelta = 4,
    statWindowSize = 10,
    historyWindowSize = 255,
    resetMsThreshold = 1000,
    wsLinkTopic = 'trame.rca.topic.stream',
    packetDecorator,
    onStats,
    onResize,
  } = {}) {
    this.source = source;
    this.name = name;
    this.fpsDelta = fpsDelta;
    this.statWindowSize = statWindowSize;
    this.historyWindowSize = historyWindowSize;
    this.resetMsThreshold = resetMsThreshold;
    this.wsLinkTopic = wsLinkTopic;
    this.packetDecorator = packetDecorator;
    this.onStats = onStats;
    this.onResize = onResize;

    this.rootElement = null;
    this.canvas = null;
    this.monitor = null;
    this.session = null;
    this.subscription = null;
    this.observer = null;
    this.handler = null;
    this.cw = 200;
    this.ch = 200;
  }

  mount({ root, canvas }) {
    this.rootElement = root;
    this.canvas = canvas;
    this.monitor = new FPSMonitor(
      this.historyWindowSize,
      this.statWindowSize,
      this.resetMsThreshold
    );

    this.handler = ([v]) => {
      const decorate = this.packetDecorator || DEFAULT_PACKET_DECORATOR;
      const { name, serverTime, contentSize } = decorate(v);
      if (this.name !== name) {
        return;
      }
      const stats = this.monitor.addEntry(serverTime, contentSize);
      if (stats) {
        this.onStats?.({
          avg: stats.avgFps,
          totalSize: stats.totalSize,
          delta: 1000 / (stats.minMax[1] - stats.minMax[0]),
        });
        this.draw(stats.client, stats.server);
      }
    };

    this.session = getSession(this.source);
    this.subscription = subscribe(
      this.session,
      this.wsLinkTopic,
      this.handler
    );

    this.observer = new ResizeObserver(() => {
      if (!this.rootElement) {
        return;
      }
      const { width, height } = this.rootElement.getBoundingClientRect();
      this.cw = width;
      this.ch = height;
      this.onResize?.({ cw: width, ch: height });
    });
    this.observer.observe(this.rootElement);
  }

  draw(client, server, clientColor = '#1DE9B688', serverColor = '#EF9A9A') {
    if (!this.canvas) {
      return;
    }
    const width = this.cw;
    const height = this.ch;
    const ctx = this.canvas.getContext('2d');

    const centerHeight = Math.floor(height * 0.5 + 0.5);
    const yScale = centerHeight / (1001 * this.fpsDelta);
    const xScale = width / (client.length - 2);

    ctx.clearRect(0, 0, width, height);

    // ref
    ctx.strokeStyle = 'black';
    ctx.beginPath();
    ctx.moveTo(0, centerHeight);
    ctx.lineTo(width, centerHeight);
    ctx.stroke();
    ctx.strokeStyle = '#eee';
    for (let i = 0; i < this.fpsDelta; i++) {
      ctx.beginPath();
      ctx.moveTo(0, centerHeight + 1000 * (i + 1) * yScale);
      ctx.lineTo(width, centerHeight + 1000 * (i + 1) * yScale);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, centerHeight - 1000 * (i + 1) * yScale);
      ctx.lineTo(width, centerHeight - 1000 * (i + 1) * yScale);
      ctx.stroke();
    }

    // client
    ctx.strokeStyle = clientColor;
    ctx.lineWidth = 8;
    ctx.beginPath();
    ctx.moveTo(0, centerHeight - yScale * client[1]);
    for (let i = 2; i < client.length; i++) {
      ctx.lineTo((i - 1) * xScale, centerHeight - yScale * client[i]);
    }
    ctx.stroke();

    // server
    ctx.strokeStyle = serverColor;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, centerHeight - yScale * server[1]);
    for (let i = 2; i < server.length; i++) {
      ctx.lineTo((i - 1) * xScale, centerHeight - yScale * server[i]);
    }
    ctx.stroke();
  }

  sizeUnit(v) {
    return formatSizeUnit(v);
  }

  setFpsDelta(v) {
    this.fpsDelta = v;
  }

  setName(v) {
    this.name = v;
  }

  setStatWindowSize(v) {
    if (this.monitor) {
      this.monitor.windowStatSize = v;
    }
  }

  setHistoryWindowSize(v) {
    if (this.monitor) {
      this.monitor.windowSize = v;
    }
  }

  setResetMsThreshold(v) {
    if (this.monitor) {
      this.monitor.newInteractionThreshold = v;
    }
  }

  unmount() {
    if (this.observer && this.rootElement) {
      this.observer.unobserve(this.rootElement);
    }
    unsubscribe(this.session, this.subscription);
    this.subscription = null;
    this.rootElement = null;
    this.canvas = null;
  }
}
