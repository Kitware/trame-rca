import ImageDisplayArea from './ImageDisplayArea.js';
import MediaSourceDisplayArea from './MediaSourceDisplayArea.js';
import VideoDecoderDisplayArea from './VideoDecoderDisplayArea.js';
import RawImageDisplayArea from './RawImageDisplayArea.js';
import SharedTextureDisplayArea from './SharedTextureDisplayArea.js';

export default {
  components: {
    ImageDisplayArea,
    MediaSourceDisplayArea,
    VideoDecoderDisplayArea,
    RawImageDisplayArea,
    SharedTextureDisplayArea,
  },
  props: {
    name: {
      type: String,
      default: 'default',
    },
    origin: {
      type: String,
      default: 'anonymous',
    },
    display: {
      type: String,
      default: 'image',
    },
    imageStyle: {
      type: Object,
      default: () => ({ width: '100%' }),
    },
    monitor: {
      type: Number,
      default: 0,
    },
  },
  template: `
    <div class="display-area">
      <image-display-area v-if="display === 'image'" :name="name" :origin="origin" :poolSize="4" :imageStyle="imageStyle" :monitor="monitor" @stats="$emit('stats', $event)" />
      <media-source-display-area v-if="display === 'media-source'" :name="name" :origin="origin" />
      <video-decoder-display-area v-if="display === 'video-decoder'" :name="name" :origin="origin" />
      <raw-image-display-area v-if="display === 'raw-image'" :name="name" :origin="origin" :imageStyle="imageStyle" />
      <shared-texture-display-area v-if="display === 'shared-texture'" :name="name" @stats="$emit('stats', $event)" />
    </div>
  `,
};
