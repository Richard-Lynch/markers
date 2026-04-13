"""
markers - Lightweight class introspection toolkit.

Public API:
    Marker      — Subclass to define markers (with optional pydantic schema).
    MarkerGroup — Subclass to bundle related markers into a .mixin.
    Registry    — Subclass to track and query across all subclasses.

Supporting types (for type hints):
    MarkerInstance — A specific usage of a marker with params.
    MemberInfo     — Metadata about a field or method.
    MemberKind     — Enum: FIELD or METHOD.
    MISSING        — Sentinel for fields with no default.
"""

from markers._types import MISSING, MarkerInstance, MemberInfo, MemberKind
from markers.groups import MarkerGroup
from markers.marker import Marker
from markers.registry import Registry

__all__ = [
    "MISSING",
    "Marker",
    "MarkerGroup",
    "MarkerInstance",
    "MemberInfo",
    "MemberKind",
    "Registry",
]
