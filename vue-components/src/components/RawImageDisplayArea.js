const { inject } = window.Vue;

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
    const trame = inject('trame');

    this.wslinkSubscription = null;
    const canvas = this.$el;
    const ctx = canvas.getContext('2d');
    this.onImage = async ([{ name, meta, content }]) => {
      if (this.name === name) {
        let imageData = null;
        if (meta.type.includes('image/rgb24')) {
          const data = content.buffer
            ? content
            : new Uint8Array(await content.arrayBuffer());
          canvas.width = meta.w;
          canvas.height = meta.h;
          imageData = ctx.createImageData(meta.w, meta.h);
          const pixels = imageData.data;
          let iRGB = 0;
          let iRGBA = 0;
          while (iRGBA < pixels.length) {
            pixels[iRGBA++] = data[iRGB++];
            pixels[iRGBA++] = data[iRGB++];
            pixels[iRGBA++] = data[iRGB++];
            pixels[iRGBA++] = 255;
          }
        } else if (meta.type.includes('image/rgba32')) {
          const data = new Uint8ClampedArray(
            content.buffer ? content : await content.arrayBuffer()
          );
          canvas.width = meta.w;
          canvas.height = meta.h;
          imageData = new ImageData(data, meta.w, meta.h);
        }
        if (imageData) {
          ctx.putImageData(imageData, 0, 0);
          // if the frame sender provided an ack_id, send back to the server
          // so they know this frame has been processed
          if (meta['ack_id'] !== undefined) {
            trame.client
              .getConnection()
              .getSession()
              .call('trame.rca.ack_id', [this.name, meta['ack_id']]);
          }
          // if the frame sender provide user_data, emit as a client event
          if (meta['user_data'] !== undefined) {
            this.$emit('user_data', meta['user_data']);
          }
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
