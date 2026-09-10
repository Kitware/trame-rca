import { watchEffect, ref, inject, onBeforeUnmount, provide } from 'vue';
import { ImageStreamController } from 'trame-rca-js';

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

    const controller = new ImageStreamController({
      source: { trame },
      name: props.name,
      poolSize: props.poolSize,
      onImage: (img) => {
        image.value = img;
      },
    });

    watchEffect(() => {
      controller.poolSize = props.poolSize;
      controller.updatePoolSize();
    });

    watchEffect(() => {
      controller.setName(props.name);
    });

    controller.mount();

    onBeforeUnmount(() => {
      controller.unmount();
    });

    provide('rcaImageStream', image);
    provide('rcaImageStreamName', props.name);

    return {
      image,
    };
  },
  template: `<slot class="image-stream" :image="image"></slot>`,
};
