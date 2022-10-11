from wslink import register as exportRpc
from wslink.websocket import LinkProtocol


class AreaAdapter:
    def __init__(self, name):
        self.area_name = name
        self.streamer = None
        self.last_meta = None

    def set_streamer(self, stream_manager):
        self.streamer = stream_manager

    def update_size(self, origin, size):
        width = size.get("w", 300)
        height = size.get("h", 300)
        device_pixel_ratio = size.get("p", 1)
        print(f"{origin}: {width}x{height} - PixelRatio: {device_pixel_ratio}")

    def push(self, content, meta=None):
        if meta is not None:
            self.last_meta = meta
        self.streamer.push_content(self.area_name, self.last_meta, content)

    def on_interaction(self, origin, event):
        event_type = event.get("t", "mouse-down")
        position = event.get("p", (0, 0))
        modifier_shift = event.get("shift", 0)
        modifier_ctrl = event.get("ctrl", 0)
        modifier_alt = event.get("alt", 0)
        modifier_cmd = event.get("cmd", 0)
        modifier_fn = event.get("fn", 0)
        print(f"{origin}::{event_type}: {position}")
        print(
            f"Modifier: shift({modifier_shift}), ctrl({modifier_ctrl}), alt({modifier_alt}), command({modifier_cmd}), fn({modifier_fn})"
        )


class StreamManager(LinkProtocol):
    def __init__(self):
        super().__init__()
        self._area_adapters = {}

    def register_area(self, area_adapter):
        self._area_adapters[area_adapter.area_name] = area_adapter
        area_adapter.set_streamer(self)

    def unregister_area(self, area_name):
        adapter = self._area_adapters.pop(area_name)
        adapter.set_streamer(None)

    @exportRpc("trame.rca.size")
    def update_size(self, area_name, origin, size):
        adapter = self._area_adapters.get(area_name, None)
        if adapter:
            adapter.update_size(origin, size)
        else:
            print(f"No area {area_name} available for size")

    @exportRpc("trame.rca.push")
    def push_content(self, area_name, metadata, content):
        self.publish(
            "trame.rca.topic.stream",
            dict(name=area_name, meta=metadata, content=self.addAttachment(content)),
        )

    @exportRpc("trame.rca.event")
    def on_interaction(self, area_name, origin, event):
        adapter = self._area_adapters.get(area_name, None)
        if adapter:
            adapter.on_interaction(origin, event)
        else:
            print(f"No area {area_name} available for event")
