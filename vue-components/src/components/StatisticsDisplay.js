import { FPSMonitor } from '../utils/FpsMonitor';

const UNITS = ['B/s', 'KB/s', 'MB/s'];

export default {
  props: {
    name: {
      type: String,
      default: 'default',
    },
    fpsDelta: {
      type: Number,
      default: 4,
    },
    statWindowSize: {
      type: Number,
      default: 10,
    },
    historyWindowSize: {
      type: Number,
      default: 255,
    },
    resetMsThreshold: {
      type: Number,
      default: 255,
    },
    wsLinkTopic: {
      type: String,
      default: 'trame.rca.topic.stream',
    },
    packetDecorator: {
      type: Function,
      default: ({ name, meta, content }) => ({
        name,
        serverTime: meta.st,
        contentSize: content.length,
      }),
    },
  },
  data() {
    return {
      cw: 200,
      ch: 200,
      avg: 30,
      delta: 2,
      totalSize: 0,
    };
  },
  watch: {
    statWindowSize(v) {
      this.monitor.windowStatSize = v;
    },
    historyWindowSize(v) {
      this.monitor.windowSize = v;
    },
    resetMsThreshold(v) {
      this.monitor.newInteractionThreshold = v;
    },
  },
  expose: ['sizeUnit'],
  methods: {
    sizeUnit(v) {
      let value = v;
      for (let i = 0; i < 3; i++) {
        if (value < 1000) {
          return `${value.toFixed(1)} ${UNITS[i]}`;
        }
        value /= 1000;
      }
    },
    cleanup() {
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
    this.monitor = new FPSMonitor(this.historyWindowSize, this.statWindowSize);

    // Display stream
    this.wslinkSubscription = null;
    this.onStreamPacket = ([v]) => {
      const { name, serverTime, contentSize } = this.packetDecorator(v);
      if (this.name === name) {
        const stats = this.monitor.addEntry(serverTime, contentSize);
        if (stats) {
          this.avg = stats.avgFps;
          this.totalSize = stats.totalSize;
          this.delta = 1000 / (stats.minMax[1] - stats.minMax[0]);
          this.draw(stats.client, stats.server);
        }
      }
    };
    if (this.trame) {
      this.wslinkSubscription = this.trame.client
        .getConnection()
        .getSession()
        .subscribe(this.wsLinkTopic, this.onStreamPacket);
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
  // support both vue2 and vue3 unmount callbacks
  beforeDestroy() {
    this.cleanup();
  },
  beforeUnmount() {
    this.cleanup();
  },
  inject: ['trame'],
  template: `
    <v-col style="width: 100%; height: 100%; position: relative;">
      <v-row class="text-subtitle-2" style="position: absolute; top: 0; left: 0; width: 100%; z-index: 1;">
        <v-icon>mdi-gauge</v-icon>
        <v-spacer />
        <div>
          {{ avg.toFixed(1) }} fps
        </div>
        <v-spacer />
        <v-icon>mdi-database-import</v-icon>
        <v-spacer />
        <div>
          {{ sizeUnit(totalSize) }}
        </div>
      </v-row>
      <canvas style="position: absolute; left: 0; top: 0;" class="js-canvas" :width="cw" :height="ch">
      </canvas>
    </v-col>
  `,
};
