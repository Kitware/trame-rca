// Type declarations for the framework-agnostic trame-rca core (`trame-rca-js`).
// The implementation is plain ESM JavaScript; this file mirrors the public API
// exported from `src/index.js`.

/**
 * A "source" is anything exposing a `trame` reference: a Vue component
 * instance, a React props object, or `{ trame }`.
 */
export interface TrameSource {
  trame?: Trame | null;
}

export type TrameSourceLike = TrameSource | null | undefined;

export interface TrameSession {
  call(topic: string, args?: unknown[]): Promise<unknown>;
  subscribe(topic: string, callback: (args: unknown[]) => void): unknown;
  unsubscribe(subscription: unknown): void;
}

export interface TrameConnection {
  getSession(): TrameSession;
}

export interface TrameClient {
  getConnection(): TrameConnection;
}

export interface Trame {
  client?: TrameClient;
}

export function getTrame(source?: TrameSourceLike): Trame | null;
export function getSession(source?: TrameSourceLike): TrameSession | undefined;
export function subscribe(
  session: TrameSession | null | undefined,
  topic: string,
  callback: (args: unknown[]) => void,
): unknown | null;
export function unsubscribe(
  session: TrameSession | null | undefined,
  subscription: unknown,
): void;

/** Meta payload attached to a streamed packet. */
export interface StreamMeta {
  type: string;
  st: number;
  w?: number;
  h?: number;
  key?: 'key' | 'delta';
  codec?: string;
  [key: string]: unknown;
}

/** Binary content of a streamed packet, as delivered by wslink. */
export type StreamContent = Uint8Array | Blob;

/** A single entry of the `trame.rca.topic.stream` subscription. */
export interface StreamPacket {
  name: string;
  meta: StreamMeta;
  content: StreamContent;
}

/** Size event emitted by the remote controlled area / image region. */
export type RcaSizeEvent = {
  w: number;
  h: number;
  p: number;
};

// ---------------------------------------------------------------------------
// utils
// ---------------------------------------------------------------------------

export interface FPSStats {
  avgFps: number;
  client: number[];
  server: number[];
  minMax: [number, number];
  totalSize: number;
}

export class FPSMonitor {
  constructor(
    windowSize?: number,
    windowStatSize?: number,
    newInteractionThreshold?: number,
    fpsWindowMs?: number,
  );
  windowSize: number;
  windowStatSize: number;
  newInteractionThreshold: number;
  fpsWindowMs: number;
  lastTS: number;
  serverTime: number[];
  clientTimes: number[];
  packetSizes: number[];
  statWindow: number[];
  fpsWindow: number[];
  trim(): void;
  compute(): FPSStats | null;
  addEntry(timeInMs: number, size: number): FPSStats | null;
}

export class FunctionThrottle {
  constructor(fn: (...args: any[]) => void, throttleTimeMs?: number);
  isThrottled: boolean;
  argsToUse: unknown[] | null;
  delay: number;
  run(...args: any[]): void;
}

export class EventThrottle {
  constructor(
    processCallback: (event: unknown) => unknown,
    throttleTimeMs?: number,
  );
  eventQueue: unknown[];
  processing: boolean;
  throttleTimeMs: number;
  processCallback: (event: unknown) => unknown;
  eventKeysToIgnore: Set<string>;
  compressEvents(events: unknown[]): unknown[];
  canCompressEvents(prev: unknown, next: unknown): boolean;
  sendEvent(event: unknown): void;
}

export class DecoderWorker {
  constructor();
  worker: Worker | null;
  codec: string;
  width: number;
  height: number;
  bindCanvas(domCanvas: HTMLCanvasElement): void;
  setContentType(codec: string, codedWidth: number, codedHeight: number): void;
  pushChunk(timestamp: number, type: 'key' | 'delta', data: Uint8Array): void;
  flush(): void;
  reset(): void;
  terminate(): void;
}

export class ImageFrame {
  constructor(onLoad?: (img: HTMLImageElement, url: string) => void);
  onLoad?: (img: HTMLImageElement, url: string) => void;
  img: HTMLImageElement;
  pending: boolean;
  url: string;
  blob: Blob | null;
  update(type: string, content: BlobPart): boolean;
}

export interface TranslatedEvent {
  x?: number;
  y?: number;
  w?: number;
  h?: number;
  [key: string]: unknown;
}

export class EventTranslator {
  fullWidth: number;
  fullHeight: number;
  xOffset: number;
  yOffset: number;
  xSize: number;
  ySize: number;
  translate(event: TranslatedEvent): TranslatedEvent;
}

export function sizeUnit(v: number): string;

// ---------------------------------------------------------------------------
// media
// ---------------------------------------------------------------------------

export interface RawImageMeta {
  type: string;
  w: number;
  h: number;
  [key: string]: unknown;
}

export function drawRawImage(
  canvas: HTMLCanvasElement,
  meta: RawImageMeta,
  content: StreamContent,
): Promise<boolean>;

export class MseVideoDecoder {
  constructor(videoElement: HTMLVideoElement, mime?: string);
  videoElement: HTMLVideoElement;
  mime: string;
  sourceBuffer: SourceBuffer | null;
  mediaSource: MediaSource | null;
  initSegment: Uint8Array | null;
  mediaSegments: Uint8Array[];
  loaded: number;
  initSourceBuffer(): void;
  queueChunk(data: Uint8Array): void;
  exit(): void;
}

// ---------------------------------------------------------------------------
// controllers
// ---------------------------------------------------------------------------

export interface ImageDisplayAreaStats {
  fps: number;
  bps: number;
  st: number;
}

export interface ImageDisplayAreaControllerOptions {
  source?: TrameSourceLike;
  name?: string;
  poolSize?: number;
  monitor?: number;
  onStats?: (stats: ImageDisplayAreaStats) => void;
  onDisplayUrl?: (url: string) => void;
  onHasContent?: (hasContent: boolean) => void;
}

export class ImageDisplayAreaController {
  constructor(options?: ImageDisplayAreaControllerOptions);
  source: TrameSourceLike;
  name: string;
  poolSize: number;
  monitor: number;
  updatePoolSize(): void;
  updateMonitorWindow(): void;
  resetContent(): void;
  setName(value: string): void;
  mount(): void;
  unmount(): void;
}

export interface RawImageDisplayAreaControllerOptions {
  source?: TrameSourceLike;
  name?: string;
  onHasContent?: (hasContent: boolean) => void;
}

export class RawImageDisplayAreaController {
  constructor(options?: RawImageDisplayAreaControllerOptions);
  setName(value: string): void;
  mount(canvas: HTMLCanvasElement | null): void;
  unmount(): void;
}

export interface MediaSourceDisplayAreaControllerOptions {
  source?: TrameSourceLike;
  name?: string;
  onHasContent?: (hasContent: boolean) => void;
  onPushSize?: (addOn: Record<string, unknown>) => void;
}

export class MediaSourceDisplayAreaController {
  constructor(options?: MediaSourceDisplayAreaControllerOptions);
  setName(value: string): void;
  requestInitializationSegment(): void;
  mount(videoElement: HTMLVideoElement | null): void;
  unmount(): void;
}

export interface VideoDecoderDisplayAreaControllerOptions {
  source?: TrameSourceLike;
  name?: string;
  onSupported?: (supported: boolean) => void;
}

export class VideoDecoderDisplayAreaController {
  constructor(options?: VideoDecoderDisplayAreaControllerOptions);
  isSupported: boolean;
  setName(value: string): void;
  mount(canvas: HTMLCanvasElement | null): void;
  unmount(): void;
}

export interface StatisticsSample {
  name: string;
  serverTime: number;
  contentSize: number;
}

export interface StatisticsDisplayStats {
  avg: number;
  totalSize: number;
  delta: number;
}

export interface StatisticsDisplayControllerOptions {
  source?: TrameSourceLike;
  name?: string;
  fpsDelta?: number;
  statWindowSize?: number;
  historyWindowSize?: number;
  resetMsThreshold?: number;
  wsLinkTopic?: string;
  packetDecorator?: (packet: unknown) => StatisticsSample;
  onStats?: (stats: StatisticsDisplayStats) => void;
  onResize?: (size: { cw: number; ch: number }) => void;
}

export class StatisticsDisplayController {
  constructor(options?: StatisticsDisplayControllerOptions);
  name: string;
  fpsDelta: number;
  sizeUnit(v: number): string;
  setName(v: string): void;
  setFpsDelta(v: number): void;
  setStatWindowSize(v: number): void;
  setHistoryWindowSize(v: number): void;
  setResetMsThreshold(v: number): void;
  mount(context: {
    root: HTMLElement | null;
    canvas: HTMLCanvasElement | null;
  }): void;
  unmount(): void;
}

export interface ImageStreamControllerOptions {
  source?: TrameSourceLike;
  name?: string;
  poolSize?: number;
  onImage?: (img: HTMLImageElement) => void;
}

export class ImageStreamController {
  constructor(options?: ImageStreamControllerOptions);
  name: string;
  poolSize: number;
  setName(value: string): void;
  updatePoolSize(): void;
  nextFrame(): ImageFrame;
  mount(): void;
  unmount(): void;
}

export type ImageRegionBounds = [number, number, number, number];

export interface ImageRegionControllerOptions {
  source?: TrameSourceLike;
  name?: string;
  bounds?: ImageRegionBounds;
  enableInteraction?: boolean;
  sendMouseMove?: boolean;
  sendMouseClick?: boolean;
  eventThrottleMs?: number;
  getImage?: () => HTMLImageElement | null | undefined;
  onSize?: (event: RcaSizeEvent) => void;
}

export class ImageRegionController {
  constructor(options?: ImageRegionControllerOptions);
  name: string;
  bounds: ImageRegionBounds | undefined;
  mount(context: {
    root: HTMLElement | null;
    canvas: HTMLCanvasElement | null;
  }): void;
  draw(): void;
  setBounds(bounds: ImageRegionBounds): void;
  setEnableInteraction(value: boolean): void;
  setSendMouseClick(value: boolean): void;
  setSendMouseMove(value: boolean): void;
  setEventThrottleMs(value: number): void;
  sendEvent(event: unknown): void;
  unmount(): void;
}

export interface RemoteControlledAreaControllerOptions {
  source?: TrameSourceLike;
  name?: string;
  origin?: string;
  sendMouseMove?: boolean;
  eventThrottleMs?: number;
  resizeThrottleMs?: number;
}

export class RemoteControlledAreaController {
  constructor(options?: RemoteControlledAreaControllerOptions);
  name: string;
  origin: string;
  mount(root: HTMLElement | null): void;
  sendEvent(event: unknown): void;
  pushSize(addOn?: Record<string, unknown>): void;
  setName(value: string): void;
  setOrigin(value: string): void;
  setEventThrottleMs(value: number): void;
  setResizeThrottleMs(value: number): void;
  setSendMouseMove(value: boolean): void;
  unmount(): void;
}
