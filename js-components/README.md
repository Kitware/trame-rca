# trame-rca JS Components

Framework-agnostic core shared by the `vue-components` and `react-components` packages.

This package owns everything that does not depend on Vue or React:

- `src/utils/` – `FPSMonitor`, `EventThrottle`, `decoder` (WebCodecs worker),
  `interactorStyle` (vtk.js), `ImageFrame`, `EventTranslator`.
- `src/media/` – `MseVideoDecoder` and raw RGB24/RGBA32 canvas rendering.
- `src/controllers/` – stateful controllers (frame pools, stream subscriptions,
  throttling, input capture) consumed by the framework adapters.
- `src/style.css` – the single source of the shared stylesheet.

`@kitware/vtk.js` is declared here and resolved transitively by the framework packages,
so there is exactly one vtk.js instance at runtime.

> This package must not import `vue` or `react`.

## Usage

The package is plain ESM and is consumed directly from `src` by the framework builds
(there is no separate build artifact). TypeScript declarations for the public API are
shipped alongside it in `src/index.d.ts`:

```js
import { RemoteControlledAreaController } from 'trame-rca-js';
```

## Tests

```bash
npm install
npm run test
npm run lint
```
