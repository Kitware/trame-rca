import { describe, expect, it } from 'vitest';

import { EventTranslator } from '../EventTranslator.js';

describe('EventTranslator', () => {
  it('maps region coordinates back to the full image', () => {
    const translator = new EventTranslator();
    Object.assign(translator, {
      fullWidth: 1000,
      fullHeight: 500,
      xOffset: 100,
      xSize: 200,
      yOffset: 50,
      ySize: 100,
    });
    expect(translator.translate({ x: 50, y: 25, w: 200, h: 100 })).toEqual({
      x: 150,
      y: 75,
      w: 1000,
      h: 500,
    });
  });

  it('passes through events without a position', () => {
    const event = { type: 'StartInteractionEvent' };
    expect(new EventTranslator().translate(event)).toEqual(event);
  });
});
