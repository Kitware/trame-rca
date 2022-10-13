class FPSMonitor {
  constructor(
    windowSize = 255,
    windowStatSize = 10,
    newInteractionThreshold = 1000
  ) {
    this.windowSize = windowSize;
    this.windowStatSize = windowStatSize;
    this.newInteractionThreshold = newInteractionThreshold;
    this.lastTS = 0;
    this.serverTime = [];
    this.clientTimes = [];
    this.statWindow = [];
  }

  trim() {
    while (this.serverTime.length > this.windowSize) {
      this.serverTime.shift();
      this.clientTimes.shift();
    }
    while (this.statWindow.length > this.windowStatSize) {
      this.statWindow.shift();
    }
  }

  compute() {
    if (this.statWindow.length < 2) {
      return null;
    }
    const start = this.statWindow[0];
    const end = this.statWindow[this.statWindow.length - 1];
    const dt = (end - start) / (this.statWindow.length - 1);
    const avgFps = 1000 / dt;
    const client = [];
    const server = [];
    const minMax = [0, 0];
    let clientTime = this.clientTimes[0];
    let serverTime = this.serverTime[0];
    for (let i = 0; i < this.clientTimes.length; i++) {
      const ct = this.clientTimes[i] - clientTime;
      const st = this.serverTime[i] - serverTime;
      client.push(ct);
      server.push(st);
      clientTime += dt;
      serverTime += dt;

      const minValue = ct < st ? ct : st;
      const maxValue = ct > st ? ct : st;

      if (minMax[0] > minValue) {
        minMax[0] = minValue;
      }
      if (minMax[1] < maxValue) {
        minMax[1] = maxValue;
      }
    }

    return {
      avgFps,
      client,
      server,
      minMax,
    };
  }

  addEntry(timeInMs) {
    const ts = Date.now();
    this.serverTime.push(timeInMs);
    this.clientTimes.push(ts);
    if (ts - this.lastTS < this.newInteractionThreshold) {
      this.statWindow.push(ts);
    } else {
      this.statWindow.length = 0;
    }
    this.lastTS = ts;
    this.trim();
    return this.compute();
  }
}

export default {
  name: 'FpsDisplay',
  props: {
    name: {
      type: String,
      default: 'default',
    },
    fpsDelta: {
      type: Number,
      default: 4,
    },
  },
  data() {
    return {
      cw: 200,
      ch: 200,
      avg: 30,
      delta: 2,
    };
  },
  methods: {
    draw(client, server, clientColor = '#1DE9B688', serverColor = '#EF9A9A') {
      if (!this.$el) {
        return;
      }
      const { cw: width, ch: height } = this;
      const canvas = this.$el.querySelector('.js-canvas');
      const ctx = canvas.getContext('2d');

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
    },
  },
  created() {
    this.monitor = new FPSMonitor();

    // Display stream
    this.wslinkSubscription = null;
    this.onStreamPacket = ([{ name, meta }]) => {
      if (this.name === name) {
        const stats = this.monitor.addEntry(meta.st);
        if (stats) {
          this.avg = stats.avgFps;
          this.delta = 1000 / (stats.minMax[1] - stats.minMax[0]);
          this.draw(stats.client, stats.server);
        }
      }
    };
    if (this.trame) {
      this.wslinkSubscription = this.trame.client
        .getConnection()
        .getSession()
        .subscribe('trame.rca.topic.stream', this.onStreamPacket);
    }

    // Size management
    this.observer = new ResizeObserver(() => {
      if (!this.$el) {
        return;
      }
      const { width, height } = this.$el.getBoundingClientRect();
      this.cw = width;
      this.ch = height;
    });
  },
  mounted() {
    this.observer.observe(this.$el);
  },
  beforeUnmount() {
    this.observer.unobserve(this.$el);
    if (this.wslinkSubscription) {
      if (this.trame) {
        this.trame.client
          .getConnection()
          .getSession()
          .unsubscribe(this.wslinkSubscription);
        this.wslinkSubscription = null;
      }
    }
  },
  inject: ['trame'],
};
