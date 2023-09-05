from pathlib import Path
from ..protocol import StreamManager

serve_path = str(Path(__file__).with_name("serve").resolve())
serve = {"__trame_rca": serve_path}
scripts = ["__trame_rca/trame-rca.umd.js"]
vue_use = ["trame_rca"]


def setup(server, **kwargs):
    def configure_protocol(root_protocol):
        protocol_instance = StreamManager()
        server.controller.rc_area_register = protocol_instance.register_area
        server.controller.rc_area_unregister = protocol_instance.unregister_area
        root_protocol.registerLinkProtocol(protocol_instance)

    server.add_protocol_to_configure(configure_protocol)
