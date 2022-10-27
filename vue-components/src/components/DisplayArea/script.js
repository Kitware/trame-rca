import ImageDisplayArea from '../ImageDisplayArea';
import MediaSourceDisplayArea from '../MediaSourceDisplayArea';
import VideoDecoderDisplayArea from '../VideoDecoderDisplayArea';
import RawImageDisplayArea from '../RawImageDisplayArea';

export default {
  name: 'DisplayArea',
  components: {
    ImageDisplayArea,
    MediaSourceDisplayArea,
    VideoDecoderDisplayArea,
    RawImageDisplayArea,
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
  },
};
