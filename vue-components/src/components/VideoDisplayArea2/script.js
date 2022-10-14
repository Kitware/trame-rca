// IDL for communicating with videoWorker.
class VideoWorkerMessage {
  constructor() {
    // to create the VideoDecoder and set up handlers.
    this.init = false;
    // configures the VideoDecoder with codec, codedWidth, codedHeight
    this.reconfigure = false;
    // process a chunk of data. calls VideoDecoder.decode(chunk)
    this.process_chunk = false;
    // tells the worker to flush decoder.
    this.flush = false;
    // tells worker to reset decoder.
    this.reset = false;
    // tells worker to close decoder.
    this.close_decoder = false;
    // a chunk's timestamp in microseconds. comes from encoder.
    this.timestamp = 0;
    // is this chunk key? or delta? comes from encoder.
    this.type = 'key';
    // the data of a chunk. it can be a DataView or ArrayBuffer.
    this.data = null;
    // a config object for the encoder. fill it up as per spec when requesting a reconfigure.
    this.config = null;
    // a canvas that the decoder will render into.
    this.canvas = null;
  }
}

export default {
  name: 'VideoDisplayArea2',
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
      // this component has content when chunks have been or will eventually be decoded.
      // TODO: I'm not sure if this is the cause for temporary white screen after switching b/w jpg and vp9 repeatedly.
      hasContent: false,
      // decoder is 'ready' after it's configured.
      decoderReady: false,
      // let's start with sensible defaults.
      width: 640,
      height: 480,
      codec: '',
    };
  },
  methods: {
    startWorker(w = 640, h = 480) {
      // we load the worker with script from 'template.html'
      // WARNING: As a result, comments should not be placed in that <script> element.
      let workerCodeText = document.querySelector('#videoWorker').textContent;
      const blob = new Blob([workerCodeText]);
      // console.log(`workerCodeText: ${workerCodeText}`);
      this.worker = new Worker(URL.createObjectURL(blob));
      // so that we know something went wrong creating that worker.
      this.worker.addEventListener(
        'error',
        () => {
          console.error('worker failed');
        },
        false
      );
      this.worker.onmessage = (e) => {
        // Recreates worker in case of a decoder error.
        console.log(`Worker message: ${e.data}`);
        this.worker.terminate();
        this.startWorker(this.width, this.height);
      };
      // every time a worker is created, it will want to own a canvas for rendering.
      const dstCanvas = document.createElement('canvas');
      dstCanvas.width = w;
      dstCanvas.height = h;
      this.width = w;
      this.height = h;
      let dst = document.getElementById('rendererArea');
      if (dst.children.item(1)) {
        dst.removeChild(dst.children.item(1));
      }
      dst.appendChild(dstCanvas);
      // decoder worker will take over control of rendering.
      let offscreen = dstCanvas.transferControlToOffscreen();
      // let's initialize the decoder.
      let message = new VideoWorkerMessage();
      message.init = true;
      message.canvas = offscreen;
      // send canvas as a transferable.
      this.worker.postMessage(message, [offscreen]);
      this.decoderReady = false;
    },
    destroyDecoder() {
      // close the decoder completely.
      let message = new VideoWorkerMessage();
      message.close_decoder = true;
      this.worker.postMessage(message);
      // destroy the worker.
      this.worker.terminate();
      this.hasContent = false;
      this.decoderReady = false;
      return;
    },
  },
  mounted() {
    if (!('VideoFrame' in window)) {
      this.$el.innerHTML = '<h1>WebCodecs API is not supported.</h1>';
      return;
    }
    this.startWorker();
    this.onChunkAvailable = ([{ name, meta, content }]) => {
      // console.log(`onChunkAvailable`);
      // console.log(meta);
      // console.log(content);
      // when we do note get octet-stream or valid codec, terminate worker.
      if (
        meta.type.includes('application/octet-stream') === false ||
        meta.codec.length === 0 ||
        meta.codec.includes('unknown') === true
      ) {
        this.destroyDecoder();
      }
      if (this.name === name && meta.codec.length) {
        // detect size changes to reconfigure decoder.
        if (
          this.decoderReady === false ||
          this.width != meta.w ||
          this.height != meta.h ||
          this.codec != meta.codec
        ) {
          this.destroyDecoder();
          // let's create a new worker. it will also init the decoder and a new canvas.
          this.startWorker(meta.w, meta.h);
          this.codec = meta.codec;
          // let the decoder rconfigure for give codec, wxh.
          let message = new VideoWorkerMessage();
          message.reconfigure = true;
          message.config = {
            codec: meta.codec,
            codedWidth: meta.w,
            codedHeight: meta.h,
          };
          // console.log(
          //   `send config ${message.config.codec}|${meta.w}|${meta.h}`
          // );
          this.worker.postMessage(message);
          this.decoderReady = true;
          this.hasContent = true;
        }
        // send chunk for decoding.
        content.arrayBuffer().then((v) => {
          // let's pack up timestamp, key/delta and data in the chunk.
          let message = new VideoWorkerMessage();
          message.process_chunk = true;
          message.data = v;
          message.timestamp = meta.st;
          message.type = meta.key;
          // console.log(
          //   `send chunk ${message.timestamp}|${message.type}|${v.byteLength}`
          // );
          this.worker.postMessage(message);
        });
      }
    };
    if (this.trame) {
      this.wslinkSubscription = this.trame.client
        .getConnection()
        .getSession()
        .subscribe('trame.rca.topic.stream', this.onChunkAvailable);
    }
  },
  beforeUnmount() {
    // unsub trame.rca.topic.stream
    if (this.wslinkSubscription) {
      if (this.trame) {
        this.trame.client
          .getConnection()
          .getSession()
          .unsubscribe(this.wslinkSubscription);
        this.wslinkSubscription = null;
      }
      this.destroyDecoder();
    }
  },
  inject: ['trame', 'rcaPushSize'],
};
