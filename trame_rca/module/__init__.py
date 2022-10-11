from pathlib import Path
from ..protocol import StreamManager

# Compute local path to serve
serve_path = str(Path(__file__).with_name("serve").resolve())

# Serve directory for JS/CSS files
serve = {"__trame_rca": serve_path}

# List of JS files to load (usually from the serve path above)
scripts = ["__trame_rca/vue-trame_rca.umd.min.js"]

# List of CSS files to load (usually from the serve path above)
styles = ["__trame_rca/vue-trame_rca.css"]

# List of Vue plugins to install/load
vue_use = ["trame_rca"]


def setup(server, **kwargs):
    def configure_protocol(root_protocol):
        protocol_instance = StreamManager()
        server.controller.rc_area_register = protocol_instance.register_area
        server.controller.rc_area_unregister = protocol_instance.unregister_area
        root_protocol.registerLinkProtocol(protocol_instance)

    server.add_protocol_to_configure(configure_protocol)
