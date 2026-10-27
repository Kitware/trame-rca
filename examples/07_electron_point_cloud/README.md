# Dynamic point cloud with Electron

`app.py` moves every point of a point cloud and gives it a new color each frame, then
renders its VTK view into a GPU texture that Electron shows as is. There is a a panel that
shows the updates/s, the time spent per stage and, after a few
point counts, how many points fit in 30 or 60 updates/s.

`app_native.py` renders the same scene in a native desktop window without trame, as a
baseline: `python app_native.py [--points N] [--frames K] [--no-vsync]`.

## Run

```sh
# From the repository root, in a virtual environment
pip install -e ".[electron]" trame
cd electron
npm i
cd ..

cd examples/07_electron_point_cloud/electron
npm i
npm start
# Or pass arguments to app.py
npm start -- --points 500000 --step 250000 --target-fps 1000
```

`npm start` runs `app.py` with the `python3` of the active environment, or `$PYTHON`.
`--target-fps` (default 60) caps the update rate. `--textures` (default 2) is how many
shared textures VTK renders into in turn, also switchable at runtime in the panel: with 1,
each update waits for Electron to show the previous frame, with 2 VTK renders the next
frame meanwhile.

The frames are computed ahead each time the point count changes, `--frames` of them
(default 8), and played back and forth: an update only swaps in the next frame's arrays,
so the app work is ~0 and the timings show the pipeline alone. That costs
`--frames` × 15 bytes per point of memory. `--frames 0` computes each frame live instead.
