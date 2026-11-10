# Electron starter

The simplest `trame-rca` Electron app: `app.py` renders one surface mesh
(`vtkPartitionedDataSetCollectionSource`) into a GPU texture that Electron shows as is: no
encoding, no copy to the CPU. The Electron app in `./electron` starts `app.py` and loads its page.

## Run

```sh
# From the repository root, in a virtual environment
pip install -e ".[electron]" trame

cd examples/06_electron_starter/electron
npm i
npm start
```

`npm start` runs `app.py` with the `python3` of the active environment, or `$PYTHON`.

On Linux, if Electron fails to start with `The SUID sandbox helper binary was found, but is not
configured correctly`, allow unprivileged user namespaces:

```sh
# Ubuntu 24.04 and later
sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0
# Older distributions
sudo sysctl -w kernel.unprivileged_userns_clone=1
```
