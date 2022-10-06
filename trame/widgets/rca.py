from trame_rca.widgets.rca import *


def initialize(server):
    from trame_rca import module

    server.enable_module(module)
