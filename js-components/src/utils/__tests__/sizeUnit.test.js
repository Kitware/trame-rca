import { describe, expect, it } from 'vitest';

import { sizeUnit } from '../sizeUnit.js';

describe('sizeUnit', () => {
  it.each([
    [0, '0.0 B/s'],
    [999, '999.0 B/s'],
    [1000, '1.0 KB/s'],
    [1.5e6, '1.5 MB/s'],
    [1.5e9, '1.5 GB/s'],
  ])('formats %d as %s', (value, expected) => {
    expect(sizeUnit(value)).toBe(expected);
  });
});
