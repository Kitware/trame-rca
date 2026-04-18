from pathlib import Path

from trame_rca import __version__

from ..protocol import StreamManager

serve_path = str(Path(__file__).with_name("serve").resolve())
serve = {f"__trame_rca_{__version__}": serve_path}
scripts = [f"__trame_rca_{__version__}/trame-rca.umd.js"]
vue_use = ["trame_rca"]


def setup(server, **kwargs):
    def configure_protocol(root_protocol):
        protocol_instance = StreamManager()
        server.controller.rc_area_register = protocol_instance.register_area
        server.controller.rc_area_unregister = protocol_instance.unregister_area
        root_protocol.registerLinkProtocol(protocol_instance)

    server.add_protocol_to_configure(configure_protocol)
