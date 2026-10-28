.. |pypi_download| image:: https://kitware.github.io/trame/downloads/trame-rca.svg

=============================================
Remote Controlled Area |pypi_download|
=============================================

Remote Controlled Area widget for trame provide components
and communication infrastructure to display remote generated
image based content while allowing interaction forwarding
such as mouse, touch and multi-pointer devices.

This library aims to provide a core that can then be extended
or specialized for any backend. But its initial integration
will be focused toward VTK and/or ParaView for enabling
interactive remote rendering.
But because it aims to be generic, you should be able to rely
on its core to connect and drive any kind of backend that could
produce images/video-stream and react to mouse interaction.

License
-----------------------------------------------------------

trame-rca is made available under the Apache Software License.


Development
-----------------------------------------------------------

The client-side code is split into a framework-agnostic core (``js-components``)
and Vue/React adapters that depend on it. Install and build the core first, then
the adapter(s) you need.

.. code-block:: console

    cd js-components
    npm i

    cd ../vue-components
    npm i
    npm run build

    # optional React adapter
    cd ../react-components
    npm i
    npm run build

    cd -

Install the component

.. code-block:: console

    pip install -e .


Optional dependencies
-----------------------------------------------------------

TurboJPEG
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Faster Jpeg encoding using TurboJPEG.

**macOS system install**

.. code-block:: console

    # macOS
    brew install jpeg-turbo

**Windows install**

Download and install from Github: https://github.com/libjpeg-turbo/libjpeg-turbo/releases

**Linux install**

.. code-block:: console

    # RHEL/CentOS/Fedora
    # YUM doc: https://libjpeg-turbo.org/Downloads/YUM

    # Ubuntu: its libturbojpeg package is 2.x (2.1.5 on 24.04), but PyTurboJPEG 2
    # needs libjpeg-turbo >= 3.0, so install the official package from
    # https://github.com/libjpeg-turbo/libjpeg-turbo/releases
    sudo apt install ./libjpeg-turbo-official_<version>_<arch>.deb  # amd64 or arm64

Once your system is ready, you can try our code example:

.. code-block:: console

    pip install trame trame-vuetify vtk
    pip install "trame-rca[turbo]"

    # other encoders: jpeg, avif, turbo-jpeg, png, webp
    python ./examples/01_vtk/vtk_cone_simple.py --encoder turbo-jpeg

Video encoding with VTKStreaming
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

VTKStreaming provides tools for encoding and streaming frames from a VTK OpenGL render window using video codecs.
When NVENC is available, it enables H.264/H.265 hardware encoding; otherwise, software encoding falls back to VP9 via libvpx.

The codec is negotiated when the ``video-decoder`` display mounts: the client asks the server which codecs it can encode
(``trame.rca.video.codecs``), filters them with ``VideoDecoder.isConfigSupported``, and sends the accepted list back
(``trame.rca.video.negotiate``). The server then creates the encoder with ``vtkEncoderFactory`` preferences
``Hardware=true;Codec=<accepted list>``. No frames are pushed before negotiation. Pass ``on_video_codec`` to
``create_view_handler`` to be told what was selected (``codec``, ``backend``, ``hardware``, ``label`` or ``error``).

You can try our code example:

.. code-block:: console

    pip install trame trame-vuetify vtk
    pip install "trame-rca[vtkstreaming]"

    python ./examples/05_video/vtk_cone_simple_video.py

In order to use source-build of vtkstreaming, please clone [VTKStreaming](https://github.com/Kitware/VTKStreaming.git) one level
up outside the trame-rca directory, checkout the `wheel` branch, and install it inside the trame-rca virtual environment

.. code-block:: console

    cd ..
    git clone https://github.com/Kitware/VTKStreaming.git
    cd VTKstreaming
    uv pip install --group dev          # build deps into active venv; index from tool.uv.index
    uv pip install -e . --no-build-isolation
    cd ../trame-rca

    python ./examples/05_video/vtk_cone_simple_video.py

Shared textures with Electron
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In an Electron app, VTK can render into a GPU texture that Electron shows as is: without encoding
and without copying to the CPU. The Electron side is the ``@kitware/trame-rca-electron`` npm package in
``./electron``: it starts the trame server and loads its page. Supported on macOS (IOSurface),
Windows (D3D11 NT handles) and Linux under Wayland (dma-buf).

- macOS: works out of the box (IOSurface).
- Windows: the GL driver needs ``WGL_NV_DX_interop2``, and VTK must render on the GPU
  Chromium uses. Set ``D3D_ADAPTER=<index>`` if that isn't DXGI adapter 0.
- Linux: Wayland only for now (dma-buf). Electron duplicates the server's file descriptors
  with ``pidfd_getfd``, which needs ``kernel.yama.ptrace_scope`` at 1 or less:
  ``sudo sysctl -w kernel.yama.ptrace_scope=1``. Set ``RENDER_NODE=/dev/dri/renderD129``
  if VTK picks another GPU than the compositor.

.. code-block:: python

    from trame_rca.widgets import init_vtk_for_shared_textures
    from trame_rca.widgets import rca

    init_vtk_for_shared_textures()  # before creating any VTK render window

    # ... create render_window, then in the UI:
    view = rca.RemoteControlledArea(display="shared-texture")
    view_handler = view.create_electron_handler(render_window)

VTK renders into a ring of shared textures, by default this is 2. This allows VTK
to draw the next frame, while Electron still shows the previous one. If you're on a
mid-tier to high-end GPU, you normally do not need to use more than 1 texture because
VTK can render faster. However, on low-end hardware, it's more efficient to render the
N+k frames while electron is presenting the N'th frame. This hides the cost of each render.
The  ``create_electron_handler(..., texture_count=n)`` sets the size of this ring texture container,
and you can change it at runtime with ``view_handler.texture_count = n``. A value of 1
waits for Electron after every frame.

You can try our code example:

.. code-block:: console

    pip install trame trame-vuetify
    pip install "trame-rca[electron]"

    cd examples/06_electron/electron
    npm i
    npm start

See ``electron/README.md`` for the Electron API and what packaging an app needs.
