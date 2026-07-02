from typing import Callable, Protocol, runtime_checkable

from trame_rca.rca import RemoteControlledAreaProtocol


@runtime_checkable
class RcaRenderSchedulerProtocol(Protocol):
    """
    Protocol defining the interface for scheduling renders.

    Implementations are responsible for coordinating render requests, controlling the render rate,
    and forwarding rendered frames to the associated RCA. The scheduler typically serializes render operations
    and ensures that rendering does not exceed the configured target frame rate.

    Any class matching this interface can be used as a RCA render scheduler, regardless of inheritance.
    Implementing classes must define the required methods and properties to enable window interaction.
    """

    @property
    def rca(self) -> RemoteControlledAreaProtocol:
        """The remote controlled area (RCA) associated with this scheduler"""
        ...

    @property
    def target_fps(self) -> float:
        """Target rendering frame rate"""
        ...

    @target_fps.setter
    def target_fps(self, value: float) -> None:
        """Update the target rendering frame rate."""
        ...

    def set_push_callback(
        self,
        callback: Callable[[bytes, dict], None],
    ) -> None:
        """
        Set the callback used to deliver rendered frames.

        The callback is invoked whenever a new frame is available and receives
        the encoded frame payload together with metadata describing the frame.
        """
        ...

    def schedule_render(self) -> None:
        """
        Request a render operation.

        Implementations may execute the render immediately or defer it according
        to their scheduling strategy. Multiple calls may be coalesced to avoid
        redundant renders.
        """
        ...

    async def close(self) -> None:
        """
        Release resources held by the scheduler.

        This method should stop any background tasks, cancel pending renders,
        and perform any cleanup required before the scheduler is discarded.
        """
        ...

    def reset(self) -> None:
        """
        Re-initialize the encoder.

        This method should be called every time a client is connecting to the stream.
        """
