import ImageDisplayArea from '../ImageDisplayArea';
import VideoDisplayArea from '../VideoDisplayArea';

export default {
  name: 'DisplayArea',
  components: {
    ImageDisplayArea,
    VideoDisplayArea,
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
  },
};
