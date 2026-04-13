from typing import Any

from markers.descriptors import BaseMixin
from markers.marker import MarkerMeta

class MarkerGroupMeta(type):
    mixin: type[BaseMixin]
    _markers: dict[str, MarkerMeta]
    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> MarkerGroupMeta: ...

class MarkerGroup(metaclass=MarkerGroupMeta):
    mixin = BaseMixin
    _markers: dict[str, MarkerMeta]
