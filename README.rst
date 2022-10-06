=============================================
trame-rca: Remote Controlled Area
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
--------------------

trame-rca is made available under the Apache Software License.


Development
--------------------

Build and install the Vue components

.. code-block:: console

    cd vue-components
    npm i
    npm run build
    cd -

Install the component

.. code-block:: console

    pip install -e .
