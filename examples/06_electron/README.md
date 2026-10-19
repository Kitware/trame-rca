# Shared texture with Electron

`app.py` renders its VTK view into a GPU texture that Electron shows as is: no encoding,
no copy to the CPU. The Electron app in `./electron` starts `app.py` and loads its page.

## Run

```sh
# From the repository root, in a virtual environment
pip install -e ".[electron]" trame trame-vuetify
cd electron
npm i
cd ..

cd examples/06_electron/electron
npm i
npm start
```

`npm start` runs `app.py` with the `python3` of the active environment, or `$PYTHON`.

