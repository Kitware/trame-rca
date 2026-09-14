/* global VideoDecoder */
// Ask the server which codecs it can encode, keep the ones this browser can
// decode (server order preserved), then let the server create its encoder.
export async function probeCodecs(session, name, exclude = []) {
  const server = await session.call('trame.rca.video.codecs', [name]);
  const accepted = [];
  for (const { codec, probes } of server) {
    if (exclude.includes(codec)) continue;
    for (const probe of probes) {
      const { supported } = await VideoDecoder.isConfigSupported({
        codec: probe,
        codedWidth: 1280,
        codedHeight: 720,
      });
      if (supported) {
        accepted.push(codec);
        break;
      }
    }
  }
  return accepted;
}

export async function negotiateCodec(session, name, exclude = []) {
  const codecs = await probeCodecs(session, name, exclude);
  return session.call('trame.rca.video.negotiate', [name, codecs]);
}

const FAMILY_PREFIX = {
  avc: 'h264',
  hev: 'h265',
  hvc: 'h265',
  vp0: 'vp9',
  av0: 'av1',
};

// WebCodecs string ("avc1.42001f") -> negotiation family ("h264").
export function codecFamily(codec) {
  return FAMILY_PREFIX[(codec || '').slice(0, 3)] || codec;
}
