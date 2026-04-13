"""
markers._types - Core data types.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum, auto
from typing import Any

__all__ = ["MISSING", "MarkerInstance", "MemberInfo", "MemberKind"]

MISSING = object()


class MemberKind(Enum):
    FIELD = auto()
    METHOD = auto()


class MarkerInstance:
    """A specific usage of a Marker with validated parameters.

    Internal state is stored in underscore-prefixed slots to avoid
    collisions with schema field names on ``__getattr__`` lookup.

    Access the marker type name via ``.marker_name``.
    Access schema fields directly as attributes: ``inst.boost``, ``inst.limit``.

    Also callable as a decorator::

        @OnSave(priority=1)
        def validate(self): ...
    """

    __slots__ = ("_kwargs", "_marker_name", "_params")

    def __init__(
        self,
        marker_name: str,
        kwargs: dict[str, Any],
        params: Any = None,
    ) -> None:
        self._marker_name = marker_name
        self._kwargs = kwargs
        self._params = params

    @property
    def marker_name(self) -> str:
        """The marker type name (e.g. 'required', 'on_save')."""
        return self._marker_name

    def __call__(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Decorate a function, attaching this MarkerInstance."""
        if not callable(fn):
            raise TypeError(f"MarkerInstance '{self._marker_name}' expected a callable, got {type(fn).__name__}")
        markers: list[MarkerInstance] = list(getattr(fn, "_markers", []))
        markers.append(self)
        fn._markers = markers  # type: ignore[attr-defined]
        return fn

    def __getattr__(self, key: str) -> Any:
        """Access schema fields as attributes.

        Checks the pydantic params model first, then raw kwargs.
        Since internal state uses underscore-prefixed slots, schema
        fields like 'name', 'params', 'kwargs' work without collision.
        """
        params = self._params
        if params is not None:
            try:
                return getattr(params, key)
            except AttributeError:
                pass
        kwargs = self._kwargs
        if key in kwargs:
            return kwargs[key]
        raise AttributeError(f"MarkerInstance '{self._marker_name}' has no parameter '{key}'")

    def __repr__(self) -> str:
        if self._params is not None:
            data = self._params.model_dump()
        else:
            data = self._kwargs
        parts = [f"{k}={v!r}" for k, v in data.items()]
        return f"{self._marker_name}({', '.join(parts)})"


class MemberInfo:
    """Metadata about a single class member (field or method)."""

    __slots__ = ("default", "kind", "markers", "name", "owner", "type")

    def __init__(
        self,
        name: str,
        kind: MemberKind,
        markers: list[MarkerInstance],
        type_: Any = None,
        default: Any = MISSING,
        owner: type | None = None,
    ) -> None:
        self.name = name
        self.kind = kind
        self.type = type_
        self.markers = markers
        self.default = default
        self.owner = owner

    @property
    def is_field(self) -> bool:
        return self.kind == MemberKind.FIELD

    @property
    def is_method(self) -> bool:
        return self.kind == MemberKind.METHOD

    @property
    def has_default(self) -> bool:
        return self.default is not MISSING

    def has(self, marker_name: str) -> bool:
        return any(m._marker_name == marker_name for m in self.markers)

    def get(self, marker_name: str) -> MarkerInstance | None:
        return next((m for m in self.markers if m._marker_name == marker_name), None)

    def get_all(self, marker_name: str) -> list[MarkerInstance]:
        return [m for m in self.markers if m._marker_name == marker_name]

    def __repr__(self) -> str:
        parts = [f"name={self.name!r}", f"kind={self.kind.name}"]
        if self.type is not None:
            parts.append(f"type={self.type!r}")
        if self.markers:
            parts.append(f"markers={self.markers!r}")
        if self.has_default:
            parts.append(f"default={self.default!r}")
        if self.owner is not None:
            parts.append(f"owner={self.owner.__name__!r}")
        return f"MemberInfo({', '.join(parts)})"
