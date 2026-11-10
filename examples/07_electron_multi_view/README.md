# Electron with several views

`app.py` shows four views in a 2x2 grid. Each view has its own `vtkRenderWindow` rendering a
Klein bottle (`vtkParametricKlein` + `vtkParametricFunctionSource`) into its own shared GPU
texture. Each view can be rotated independently with the mouse.

## Run

```sh
# From the repository root, in a virtual environment
pip install -e ".[electron]" trame

cd examples/07_electron_multi_view/electron
npm i
npm start
```

`npm start` runs `app.py` with the `python3` of the active environment, or `$PYTHON`.
