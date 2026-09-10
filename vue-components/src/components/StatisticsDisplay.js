import { StatisticsDisplayController } from 'trame-rca-js';

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
      default: 1000,
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
    name(v) {
      this.controller?.setName(v);
    },
    fpsDelta(v) {
      this.controller?.setFpsDelta(v);
    },
    statWindowSize(v) {
      this.controller?.setStatWindowSize(v);
    },
    historyWindowSize(v) {
      this.controller?.setHistoryWindowSize(v);
    },
    resetMsThreshold(v) {
      this.controller?.setResetMsThreshold(v);
    },
  },
  expose: ['sizeUnit'],
  methods: {
    sizeUnit(v) {
      return this.controller?.sizeUnit(v);
    },
    cleanup() {
      this.controller?.unmount();
    },
  },
  mounted() {
    this.controller = new StatisticsDisplayController({
      source: this,
      name: this.name,
      fpsDelta: this.fpsDelta,
      statWindowSize: this.statWindowSize,
      historyWindowSize: this.historyWindowSize,
      resetMsThreshold: this.resetMsThreshold,
      wsLinkTopic: this.wsLinkTopic,
      packetDecorator: this.packetDecorator,
      onStats: ({ avg, totalSize, delta }) => {
        this.avg = avg;
        this.totalSize = totalSize;
        this.delta = delta;
      },
      onResize: ({ cw, ch }) => {
        this.cw = cw;
        this.ch = ch;
      },
    });
    this.controller.mount({
      root: this.$el,
      canvas: this.$el.querySelector('.js-canvas'),
    });
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
