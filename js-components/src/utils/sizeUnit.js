const UNITS = ['B/s', 'KB/s', 'MB/s', 'GB/s'];

export function sizeUnit(v) {
  let value = v;
  let unitIndex = 0;
  while (unitIndex < UNITS.length - 1 && value >= 1000) {
    value /= 1000;
    unitIndex += 1;
  }
  return `${value.toFixed(1)} ${UNITS[unitIndex]}`;
}
