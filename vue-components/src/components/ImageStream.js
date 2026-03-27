import { watchEffect, ref, inject, onBeforeUnmount, provide } from 'vue';

class ImageFrame {
  constructor(refImg) {
    this.refImg = refImg;
    this.img = new Image();
    this.url = '';
    this.blob = null;

    this.img.addEventListener('load', () => {
      this.refImg.value = this.img;
    });
  }

  update(type, content) {
    window.URL.revokeObjectURL(this.url);
    this.blob = new Blob([content], { type });
    this.url = URL.createObjectURL(this.blob);
    this.img.src = this.url;
  }
}

export default {
  props: {
    name: {
      type: String,
      default: 'default',
    },
    poolSize: {
      type: Number,
      default: 4,
    },
  },
  setup(props) {
    const trame = inject('trame');
    const image = ref(null);
    const frames = [];
    const subscriptions = [];
    let nextFrameIndex = 0;

    watchEffect(() => {
      while (frames.length < props.poolSize) {
        frames.push(new ImageFrame(image));
      }
      while (frames.length > props.poolSize) {
        frames.pop();
      }
    });

    function nextFrame() {
      nextFrameIndex = (nextFrameIndex + 1) % frames.length;
      return frames[nextFrameIndex];
    }

    function onImage([{ name, meta, content }]) {
      if (props.name === name) {
        nextFrame().update(meta.type, content);
      }
    }

    if (trame) {
      subscriptions.push(
        trame.client
          .getConnection()
          .getSession()
          .subscribe('trame.rca.topic.stream', onImage)
      );
    }

    onBeforeUnmount(() => {
      while (subscriptions.length) {
        const subscription = subscriptions.pop();
        if (trame) {
          trame.client.getConnection().getSession().unsubscribe(subscription);
        }
      }
    });

    provide('rcaImageStream', image);
    provide('rcaImageStreamName', props.name);

    return {
      image,
    };
  },
  template: `<slot :image="image"></slot>`,
};
