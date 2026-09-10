# Remote Controlled Area (React)

Client-side React components for `trame-rca`, registered through the trame
`client_type="react"` client.

The framework-agnostic logic shared with the Vue package lives in
`../js-components` and is consumed as a local dependency
(`"trame-rca-js": "file:../js-components"`), so it must be installed **before**
building this package. `@kitware/vtk.js` is provided transitively by
`js-components`.

## Build

```bash
# first, install the shared core (pulls @kitware/vtk.js)
cd ../js-components && npm i

# then build the React components
cd ../react-components && npm i && npm run build
```

From a clean checkout the full order is:

```
js-components  ->  vue-components  ->  react-components
```

The Vue and React bundles are emitted into the same directory
(`src/trame_rca/module/serve`), so build Vue before React (React uses
`emptyOutDir: false`).
