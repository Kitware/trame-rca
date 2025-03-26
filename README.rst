.. |pypi_download| image:: https://img.shields.io/pypi/dm/trame-rca

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

Build and install the Vue components

.. code-block:: console

    cd vue-components
    npm i
    npm run build
    cd -

Install the component

.. code-block:: console

    pip install -e .


Optional dependencies
-----------------------------------------------------------

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

    # Ubuntu
    apt-get install libturbojpeg

Once your system is ready, you can try our code example:

.. code-block:: console

    pip install trame trame-vuetify vtk
    pip install "trame-rca[turbo]"

    # other encoders: jpeg, avif, turbo-jpeg, png, webp
    python ./examples/vtk_cone_simple.py --encoder turbo-jpeg
