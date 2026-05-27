from typing import Protocol, runtime_checkable

from numpy.typing import NDArray


@runtime_checkable
class RemoteControlledAreaProtocol(Protocol):
    """
    Protocol defining the interface for interacting with a remote controlled area (RCA).

    Any class matching this interface can be used as a RCA, regardless of inheritance.
    Implementing classes must define the required methods and properties to enable RCA interaction.
    """

    @property
    def img_cols_rows(self) -> tuple[NDArray, int, int]:
        """
        Returns a tuple containing:
        - the RCA content as a NumPy array,
        - the number of columns,
        - and the number of rows.

        Called by the scheduler to render the current window view.
        """
        ...

    def process_resize_event(self, width: int, height: int) -> None:
        """
        Handle a resize event (RenderWindowInteractor).

        This method is triggered by the adapter whenever the window is resized.
        """
        ...

    def process_interaction_event(self, event: dict) -> None:
        """
        Handle an interaction event (RenderWindowInteractor).

        This method is invoked by the adapter whenever an interaction event occurs.
        Refer to the event types defined in:
        https://github.com/Kitware/vtk-js/blob/master/Sources/Rendering/Core/RenderWindowInteractor/index.js
        """
        ...
