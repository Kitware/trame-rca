from pathlib import Path

from trame_rca import __version__

from ..protocol import StreamManager

serve_path = str(Path(__file__).with_name("serve").resolve())
BASE_URL = f"__trame_rca_{__version__}"
serve = {BASE_URL: serve_path}


def setup(server, **kwargs):
    def configure_protocol(root_protocol):
        protocol_instance = StreamManager()
        server.controller.rc_area_register = protocol_instance.register_area
        server.controller.rc_area_unregister = protocol_instance.unregister_area
        root_protocol.registerLinkProtocol(protocol_instance)

    server.add_protocol_to_configure(configure_protocol)

    client_type = "vue2"
    if hasattr(server, "client_type"):
        client_type = server.client_type

    if client_type == "react":
        server.enable_module(
            {
                "scripts": [f"{BASE_URL}/trame-rca-react.umd.cjs"],
                "styles": [f"{BASE_URL}/trame-rca-react.css"],
                "react_use": ["trame_rca_react"],
            }
        )
    else:
        server.enable_module(
            {
                "scripts": [f"{BASE_URL}/trame-rca.umd.js"],
                "styles": [f"{BASE_URL}/style.css"],
                "vue_use": ["trame_rca"],
            }
        )
