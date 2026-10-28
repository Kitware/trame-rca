GL_FRAMEBUFFER = 0x8D40


class TexturePassport:
    """A cross-process abstraction for letting textures travel from Python to Electron.
    The passport has everything needed to access VTK render window's texture from another process.
    """

    # The vtkTextureObject VTK resolves its frames into, set by the subclasses.
    vtk_texture = None

    def __init__(self, render_window, width, height):
        self.render_window = render_window
        self.width = width
        self.height = height

    def to_json(self):
        """The ``texture`` message sent to the Electron main process."""
        return {}

    def attach(self):
        """Make this texture the one the render window resolves its next frames into.

        A passport attaches its texture when created: only needed when several take turns.
        """
        if self.vtk_texture is None:
            return
        self.render_window.MakeCurrent()
        display_fbo = self.render_window.GetDisplayFramebuffer()
        display_fbo.AddColorAttachment(0, self.vtk_texture)
        display_fbo.Bind()
        complete = display_fbo.CheckFrameBufferStatus(GL_FRAMEBUFFER)
        display_fbo.UnBind()
        if not complete:
            raise RuntimeError("DisplayFramebuffer incomplete with the shared texture")

    def release(self):
        """Free the texture and any OS handle to it."""

    async def flush_graphics_commands(self):
        """Wait until the GPU finished rendering into the texture."""
        self.render_window.WaitForCompletion()
