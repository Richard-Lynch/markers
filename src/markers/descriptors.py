"""
markers.descriptors - Lazy descriptors and BaseMixin.

BaseMixin carries fields/methods/members descriptors and is
automatically inherited by every MarkerGroup.mixin, so any class
using at least one group mixin gets all three for free.
"""

from markers._types import MemberInfo
from markers.core import collector

__all__: list[str] = []  # No public API — used internally by Marker


class MembersDescriptor:
    """Descriptor returning all collected members (fields + methods).

    Returns a copy to protect the internal cache from mutation.
    """

    def __get__(self, obj: object, cls: type) -> dict[str, MemberInfo]:
        return dict(collector.collect(cls))


class FieldsDescriptor:
    """Descriptor returning only field members."""

    def __get__(self, obj: object, cls: type) -> dict[str, MemberInfo]:
        return collector.fields(cls)


class MethodsDescriptor:
    """Descriptor returning only method members."""

    def __get__(self, obj: object, cls: type) -> dict[str, MemberInfo]:
        return collector.methods(cls)


class MarkerDescriptor:
    """Descriptor returning all members matching a specific marker."""

    def __init__(self, marker_name: str) -> None:
        self._marker_name = marker_name

    def __get__(self, obj: object, cls: type) -> dict[str, MemberInfo]:
        return collector.filter(cls, self._marker_name)


class BaseMixin:
    """Mixin providing fields/methods/members descriptors.

    Every Marker.mixin inherits from this, so any class using
    at least one marker mixin automatically gets these.
    """

    fields = FieldsDescriptor()
    methods = MethodsDescriptor()
    members = MembersDescriptor()
