# Electron

This directory capture several trame applications making use of electron with VTK to leverage native rendering performance of VTK.
The idea of this electron custom path is to have VTK render into a GPU texture that Electron shows as is: no
encoding, no copy to the CPU. The Electron app in `./electron` starts a trame application (`app_${name}.py`) and loads its page.

The electron sub-directory is common for all application and we can just choose at runtime which "server side" we want to exercise.

Available applications:
- __starter__: Render a simple surface mesh
- __multi_views__: shows four views in a 2x2 grid. Each view has its own `vtkRenderWindow` rendering a Klein bottle (`vtkParametricKlein` + `vtkParametricFunctionSource`) into its own shared GPU texture. Each view can be rotated independently with the mouse.
- __volume_rendering__: example mixing surface and volume rendering.
- __point_cloud__: moves every point of a point cloud and gives it a new color each frame. There is a a panel that shows the updates/s, the time spent per stage and, after a few point counts, how many points fit in 30 or 60 updates/s.

## Run

```sh
# From the repository root, in a virtual environment
uv venv
source .venv/bin/activate
uv pip install trame trame-vuetify trame-rca vtk

cd examples/06_electron_apps/electron
npm i
npm start

# Or select a specific application
TRAME_APP_NAME=starter npm start
TRAME_APP_NAME=multi_views npm start
TRAME_APP_NAME=volume_rendering npm start
TRAME_APP_NAME=point_cloud npm start -- --points 500000 --step 250000 --target-fps 1000
```

`npm start` runs the TRAME_APP with the `python3` of the active environment, or `$PYTHON`.

On Linux, if Electron fails to start with `The SUID sandbox helper binary was found, but is not
configured correctly`, allow unprivileged user namespaces:

```sh
# Ubuntu 24.04 and later
sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0
# Older distributions
sudo sysctl -w kernel.unprivileged_userns_clone=1
```

## Point Cloud application

The provided point cloud application provide additional tuning which are described below.

```
export TRAME_APP_NAME=point_cloud
```

`npm start -- --second-view` adds a second shared-texture view of the same cloud next to the
first, and spins the cameras of both views in opposite directions. The panel's timings stay
those of the first view, which now shares the GPU and the event loop with the second.

`npm start` runs `app.py` with the `python3` of the active environment, or `$PYTHON`.
`--target-fps` (default 60) caps the update rate. `--textures` (default 2) is how many
shared textures VTK renders into in turn, also switchable at runtime in the panel: with 1,
each update waits for Electron to show the previous frame, with 2 VTK renders the next
frame meanwhile. `--radii X Y Z` (default 2 1 0.5) is how far the ellipsoidal cloud spreads
along each axis.

The frames are computed ahead each time the point count changes, `--frames` of them
(default 8), and played back and forth: an update only swaps in the next frame's arrays,
so the app work is ~0 and the timings show the pipeline alone. That costs
`--frames` × 15 bytes per point of memory. `--frames 0` computes each frame live instead.
