export default {
  props: {
    name: {
      type: String,
      default: 'default',
    },
    origin: {
      type: String,
      default: 'anonymous',
    },
  },
  data() {
    return {
      hasContent: false,
    };
  },
  methods: {
    cleanup() {
      // unsub trame.rca.topic.stream
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
  },
  mounted() {
    this.wslinkSubscription = null;
    const canvas = this.$el;
    const ctx = canvas.getContext('2d');
    this.onImage = async ([{ name, meta, content }]) => {
      if (this.name === name) {
        if (meta.type.includes('image/rgb24')) {
          const data = content.buffer
            ? content
            : new Uint8Array(await content.arrayBuffer());
          canvas.width = meta.w;
          canvas.height = meta.h;
          const imageData = ctx.createImageData(meta.w, meta.h);
          const pixels = imageData.data;
          let iRGB = 0;
          let iRGBA = 0;
          while (iRGBA < pixels.length) {
            pixels[iRGBA++] = data[iRGB++];
            pixels[iRGBA++] = data[iRGB++];
            pixels[iRGBA++] = data[iRGB++];
            pixels[iRGBA++] = 255;
          }
          ctx.putImageData(imageData, 0, 0);
          this.hasContent = true;
        } else if (meta.type.includes('image/rgba32')) {
          const data = content.buffer
            ? content
            : new Uint8Array(await content.arrayBuffer());
          canvas.width = meta.w;
          canvas.height = meta.h;
          const imageData = new ImageData(data, meta.w, meta.h);
          ctx.putImageData(imageData, 0, 0);
          this.hasContent = true;
        } else {
          this.hasContent = false;
        }
      }
    };
    if (this.trame) {
      this.wslinkSubscription = this.trame.client
        .getConnection()
        .getSession()
        .subscribe('trame.rca.topic.stream', this.onImage);
    }
  },
  // support both vue2 and vue3 unmount callbacks
  beforeDestroy() {
    this.cleanup();
  },
  beforeUnmount() {
    this.cleanup();
  },
  inject: ['trame'],
  template: '<canvas class="js-canvas" v-show="hasContent"></canvas>',
};
