class TexturePassport:
    """A cross-process abstraction for letting textures travel from Python to Electron.
    The passport has everything needed to access VTK render window's texture from another process.
    """

    def __init__(self, render_window, width, height):
        self.render_window = render_window
        self.width = width
        self.height = height

    def to_json(self):
        """The ``texture`` message sent to the Electron main process."""
        return {}

    def release(self):
        """Free the texture and any OS handle to it."""

    async def flush_graphics_commands(self):
        """Wait until the GPU finished rendering into the texture."""
        self.render_window.WaitForCompletion()
