# Remote Controlled Area (Vue)

This sub-directory captures the client-side Vue components that you want to expose inside
your trame application for managing remote controlled areas along with various image
stream displays.

The framework-agnostic logic shared with the React package lives in `../js-components`.
It is consumed as a local dependency (`"trame-rca-js": "file:../js-components"`), so it
must be installed **before** building this package.

## Build

```bash
# first, install the shared core (pulls @kitware/vtk.js)
cd ../js-components && npm i

# then build the Vue components
cd ../vue-components && npm i && npm run build
```

From a clean checkout the order is always:

```
js-components  ->  vue-components
```
