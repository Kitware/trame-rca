import ImageDisplayArea from '../ImageDisplayArea';
import VideoDisplayArea from '../VideoDisplayArea';
import VideoDisplayArea2 from '../VideoDisplayArea2';

export default {
  name: 'DisplayArea',
  components: {
    ImageDisplayArea,
    VideoDisplayArea,
    VideoDisplayArea2,
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
