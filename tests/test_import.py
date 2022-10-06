def test_import():
    from trame_rca.widgets.rca import RemoteControlledArea  # noqa: F401

    # For components only, the CustomWidget is also importable via trame
    from trame.widgets.rca import RemoteControlledArea  # noqa: F401,F811
