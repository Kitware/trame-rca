declare module "@kitware/vtk.js/*";

// core types are shipped by trame-rca-js (`src/index.d.ts`)
declare module "trame-rca-js/style.css";

// provided by the trame react client
interface Window {
  trame?: any;
}
