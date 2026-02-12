export class FPSMonitor {
  constructor(
    windowSize = 255,
    windowStatSize = 10,
    newInteractionThreshold = 1000
  ) {
    this.windowSize = windowSize;
    this.windowStatSize = windowStatSize;
    this.newInteractionThreshold = newInteractionThreshold;
    this.lastTS = 0;
    this.serverTime = [];
    this.clientTimes = [];
    this.packetSizes = [];
    this.statWindow = [];
  }

  trim() {
    while (this.serverTime.length > this.windowSize) {
      this.serverTime.shift();
      this.clientTimes.shift();
      this.packetSizes.shift();
    }
    while (this.statWindow.length > this.windowStatSize) {
      this.statWindow.shift();
    }
  }

  compute() {
    if (this.statWindow.length < 2) {
      return null;
    }
    const start = this.statWindow[0];
    const end = this.statWindow[this.statWindow.length - 1];
    const dt = (end - start) / (this.statWindow.length - 1);
    const avgFps = 1000 / dt;
    const client = [];
    const server = [];
    const minMax = [0, 0];
    let clientTime = this.clientTimes[0];
    let serverTime = this.serverTime[0];
    let totalSize = 0;
    for (let i = 0; i < this.clientTimes.length; i++) {
      const ct = this.clientTimes[i] - clientTime;
      const st = this.serverTime[i] - serverTime;
      totalSize += this.packetSizes[i];
      client.push(ct);
      server.push(st);
      clientTime += dt;
      serverTime += dt;

      const minValue = ct < st ? ct : st;
      const maxValue = ct > st ? ct : st;

      if (minMax[0] > minValue) {
        minMax[0] = minValue;
      }
      if (minMax[1] < maxValue) {
        minMax[1] = maxValue;
      }
    }

    totalSize *= avgFps / this.packetSizes.length;

    return {
      avgFps,
      client,
      server,
      minMax,
      totalSize,
    };
  }

  addEntry(timeInMs, size) {
    const ts = Date.now();
    this.packetSizes.push(size);
    this.serverTime.push(timeInMs);
    this.clientTimes.push(ts);
    if (ts - this.lastTS < this.newInteractionThreshold) {
      this.statWindow.push(ts);
    } else {
      this.statWindow.length = 0;
    }
    this.lastTS = ts;
    this.trim();
    return this.compute();
  }
}
