import ImageDisplayArea from '../ImageDisplayArea';

export default {
  name: 'DisplayArea',
  components: {
    ImageDisplayArea,
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
