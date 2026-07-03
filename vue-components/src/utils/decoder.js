const INIT = 1;
const CONFIG = 2;
const CHUNK = 3;
const FLUSH = 4;
const RESET = 5;
const CLOSE = 6;

export const WORKER_CONTENT = `

function reportError(e) {
  console.log(e.message);
  postMessage(e.message);
}

function createDecoder(canvas) {
  const ctx = canvas.getContext('2d');
  const ready_frames = [];
  let underflow = true;

  function renderFrame() {
    if (ready_frames.length === 0) {
      underflow = true;
      return;
    }
    const frame = ready_frames.shift();
    underflow = false;
    ctx.drawImage(frame, 0, 0);
    frame.close();
    setTimeout(renderFrame, 0);
  }

  function handleFrame(frame) {
    ready_frames.push(frame);
    if (underflow) {
      underflow = false;
      setTimeout(renderFrame, 0);
    }
  }

  const init = {
    output: handleFrame,
    error: reportError,
  };

  return new VideoDecoder(init);
}

let decoder = null;
let debounceTimer = null;
let lastChunkData = null;
let lastChunkMeta = null;

function resetDebounceTimer() {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
    debounceTimer = null;
  }
}

function executeDebouncedDecode() {
  if (lastChunkData && decoder) {
    decoder.decode(new EncodedVideoChunk({
      timestamp: lastChunkMeta.timestamp + 1,
      type: lastChunkMeta.type,
      data: lastChunkData,
    }));
    lastChunkData = null;
    lastChunkMeta = null;
  }
}

onmessage = async function({ data: msg }) {
  switch(msg.action) {
    case 1: // init
      this.canvas = msg.canvas;
      decoder = createDecoder(this.canvas);
      break;

    case 2: // config
      this.canvas.width = msg.config.codedWidth;
      this.canvas.height = msg.config.codedHeight;
      decoder.configure({ ...msg.config, optimizeForLatency: true });
      break;

    case 3: // chunk
      resetDebounceTimer();
      lastChunkData = msg.data.slice(0);
      lastChunkMeta = { timestamp: msg.timestamp, type: msg.type };

      decoder.decode(new EncodedVideoChunk({
        timestamp: msg.timestamp,
        type: msg.type,
        data: msg.data,
      }));

      debounceTimer = setTimeout(executeDebouncedDecode, 35);
      break;

    case 4: // flush
      resetDebounceTimer();
      decoder.flush();
      break;

    case 5: // reset
      resetDebounceTimer();
      decoder.reset();
      break;

    case 6: // close
      // flush before close() to avoid currepoted state.
      // calling postMessage(flush)
      //         postMessage(close) is not enough since the second
      // abort the first before it finishes.
      resetDebounceTimer();
      await decoder.flush();
      decoder.close();
      break;
  }
}
`;

export const WORKER_JS_URL = URL.createObjectURL(new Blob([WORKER_CONTENT]));

export function createWorker() {
  const worker = new Worker(WORKER_JS_URL);
  worker.addEventListener('error', () => console.error('worker failed'), false);
  worker.onmessage = (e) => {
    console.log(`Worker message: ${e.data}`);
    console.log('>>> FIXME .....');
  };
  return worker;
}

export class DecoderWorker {
  constructor() {
    this.worker = createWorker();
    this.codec = '';
    this.width = 0;
    this.height = 0;
  }

  bindCanvas(domCanvas) {
    const action = INIT;
    const canvas = domCanvas.transferControlToOffscreen();
    this.worker.postMessage({ action, canvas }, [canvas]);
  }

  setContentType(codec, codedWidth, codedHeight) {
    if (
      this.codec !== codec ||
      this.width !== codedWidth ||
      this.height !== codedHeight
    ) {
      const action = CONFIG;
      this.codec = codec;
      this.width = codedWidth;
      this.height = codedHeight;
      this.worker.postMessage({
        action,
        config: { codec, codedWidth, codedHeight },
      });
    }
  }

  pushChunk(timestamp, type, data) {
    const action = CHUNK;
    this.worker.postMessage({ action, timestamp, type, data }, [data.buffer]);
  }

  flush() {
    this.worker.postMessage({ action: FLUSH });
  }

  reset() {
    this.worker.postMessage({ action: RESET });
  }

  terminate() {
    this.worker.postMessage({ action: CLOSE });
    // don't terminate immediately we need to wail for the video encoder to finish flushing
    // not sure how to achieve this ...
    //this.worker.terminate();
    //this.worker = null;
  }
}
