"""
markers.groups - MarkerGroup for bundling related markers.

MarkerGroup is the only way to get marker descriptors onto model classes.
Markers themselves are pure schema + factory.

    class DB(MarkerGroup):
        PrimaryKey = PrimaryKey
        Indexed = Indexed

    class User(DB.mixin):
        id: Annotated[int, DB.PrimaryKey()]

    User.primary_key  # → dict[str, MemberInfo]
    User.fields       # → dict[str, MemberInfo]
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from markers.descriptors import BaseMixin, MarkerDescriptor
from markers.marker import Marker

if TYPE_CHECKING:
    from markers.marker import MarkerMeta

__all__ = ["MarkerGroup"]


class MarkerGroupMeta(type):
    """Metaclass that auto-builds a .mixin from Marker class attributes."""

    mixin: type
    _markers: dict[str, MarkerMeta]

    def __new__(mcs, name: str, bases: tuple, namespace: dict, **kwargs: Any) -> type:
        cls = super().__new__(mcs, name, bases, namespace)

        if name == "MarkerGroup":
            return cls

        # Find all Marker subclasses assigned as class attributes
        found_markers: dict[str, MarkerMeta] = {}
        for attr, val in namespace.items():
            if isinstance(val, type) and issubclass(val, Marker) and val is not Marker:
                found_markers[attr] = val  # type: ignore[assignment]

        # Also check base groups for inherited markers
        for base in bases:
            if base is MarkerGroup:
                continue
            base_markers: dict[str, MarkerMeta] = getattr(base, "_markers", {})
            for attr, val in base_markers.items():
                if attr not in found_markers:
                    found_markers[attr] = val

        # Build mixin: BaseMixin + a MarkerDescriptor per marker
        mixin_attrs: dict[str, Any] = {}
        for marker_cls in found_markers.values():
            mark_name = marker_cls._mark_name
            mixin_attrs[mark_name] = MarkerDescriptor(mark_name)

        cls.mixin = type(f"{name}Mixin", (BaseMixin,), mixin_attrs)
        cls._markers = found_markers
        return cls


class MarkerGroup(metaclass=MarkerGroupMeta):
    """Base class for grouping related markers.

    Subclass and assign Marker subclasses as class attributes::

        class DB(MarkerGroup):
            PrimaryKey = PrimaryKey
            Indexed = Indexed

    The class automatically gets a ``.mixin`` that provides:
    - A MarkerDescriptor for each marker (e.g. ``.primary_key``, ``.indexed``)
    - ``fields``, ``methods``, ``members`` from BaseMixin

    Groups can inherit from other groups to compose::

        class FullDB(DB):
            ForeignKey = ForeignKey
    """

    _markers: dict[str, MarkerMeta] = {}
