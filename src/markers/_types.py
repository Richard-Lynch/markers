"""
markers._types - Core data types.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum, auto
from typing import Any, Generic, TypeVar

_F = TypeVar("_F", bound=Callable[..., Any])
_M = TypeVar("_M")

__all__ = ["MISSING", "CollectResult", "MarkerInstance", "MemberInfo", "MemberKind"]

class _MissingSentinel:
    """Sentinel for fields with no default value."""

    _instance: _MissingSentinel | None = None

    def __new__(cls) -> _MissingSentinel:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "MISSING"

    def __bool__(self) -> bool:
        return False


MISSING = _MissingSentinel()


class MemberKind(Enum):
    FIELD = auto()
    METHOD = auto()


class MarkerInstance:
    """A validated usage of a Marker with parameters.

    Created by calling a ``Marker`` subclass (e.g. ``MaxLen(limit=100)``).
    You don't instantiate this directly — the Marker metaclass does it.

    Accessing parameters::

        inst = Searchable(boost=2.5, analyzer="english")
        inst.marker_name  # 'searchable' — the marker type name
        inst.boost        # 2.5 — schema field access
        inst.analyzer     # 'english'

    As ``Annotated`` metadata::

        name: Annotated[str, Required(), MaxLen(limit=100)]

    As a method decorator (stacks with multiple decorators)::

        @OnSave(priority=1)
        def validate(self): ...

    Attributes:
        marker_name (str): The marker type name (e.g. 'required', 'on_save').
        <schema fields>: Access any schema field as an attribute.

    The ``repr`` shows the marker name and all parameters::

        >>> MaxLen(limit=100)
        max_length(limit=100)
        >>> Required()
        required()
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

    def __call__(self, fn: _F) -> _F:
        """Decorate a function, attaching this MarkerInstance.

        The decorated function's type signature is preserved — type checkers
        will see the original return type, not ``MarkerInstance``.

        Supports decorating ``classmethod``, ``staticmethod``, and
        ``property`` descriptors — markers are attached to the inner function.
        """
        # Unwrap descriptor wrappers to attach markers to the inner function
        if isinstance(fn, (classmethod, staticmethod)):
            inner = fn.__func__
            markers: list[MarkerInstance] = list(getattr(inner, "_markers", []))
            markers.append(self)
            inner._markers = markers  # type: ignore[attr-defined]
            return fn
        if isinstance(fn, property):
            inner = fn.fget  # type: ignore[assignment]
            markers = list(getattr(inner, "_markers", []))
            markers.append(self)
            inner._markers = markers  # type: ignore[attr-defined]
            return fn  # type: ignore[return-value]
        if not callable(fn):
            raise TypeError(
                f"MarkerInstance '{self._marker_name}' expected a callable, got {type(fn).__name__}"
            )
        markers = list(getattr(fn, "_markers", []))
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

    def as_dict(self) -> dict[str, Any]:
        """Return all marker parameters as a plain dict.

        Uses the pydantic model's ``model_dump()`` if available (includes
        defaults), otherwise returns the raw kwargs.
        """
        if self._params is not None:
            return dict(self._params.model_dump())
        return dict(self._kwargs)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MarkerInstance):
            return NotImplemented
        return self._marker_name == other._marker_name and self.as_dict() == other.as_dict()

    __hash__ = None  # type: ignore[assignment]  # mutable — unhashable

    def __repr__(self) -> str:
        data = self.as_dict()
        parts = [f"{k}={v!r}" for k, v in data.items()]
        return f"{self._marker_name}({', '.join(parts)})"


class CollectResult(dict[str, _M], Generic[_M]):
    """Dict subclass returned by ``Marker.collect_markers()``.

    Generic over the value type — ``CollectResult[MarkerInstance]`` for
    ``collect_markers()``. Type checkers using ``Self`` in the
    ``collect_markers()`` stub can infer typed marker param access.

    Maps member names to their ``MarkerInstance`` for the collected marker.
    Provides convenience methods for common patterns like uniqueness checks
    and predicate filtering.

    Usage::

        results = SM.State.collect_markers(cls)

        # Iterate with full marker access (no None checks)
        for name, marker in results.items():
            if marker.initial: ...

        # Assert exactly one match
        name, marker = results.where(lambda m: m.initial).get_one()

        # Assert at least one match
        name, marker = results.where(lambda m: m.final).get_first()

        # Filter by predicate
        finals = results.where(lambda m: m.final)
    """

    def get_one(self, label: str = "") -> tuple[str, _M]:
        """Return the single ``(name, value)`` entry.

        Raises ``ValueError`` if there are zero or more than one entries.
        The optional *label* is included in the error message for context.
        """
        if len(self) != 1:
            ctx = f" for {label!r}" if label else ""
            keys = list(self.keys())
            if len(keys) > 10:
                shown = keys[:10]
                keys_str = f"{shown} ... ({len(keys) - 10} more)"
            else:
                keys_str = str(keys)
            raise ValueError(f"Expected exactly 1 result{ctx}, found {len(self)}: {keys_str}")
        name = next(iter(self))
        return name, self[name]

    def get_one_name(self, label: str = "") -> str:
        """Return the single member name. Raises ``ValueError`` if != 1 entry."""
        name, _ = self.get_one(label)
        return name

    def get_first(self, label: str = "") -> tuple[str, _M]:
        """Return the first ``(name, value)`` entry.

        Raises ``ValueError`` if the result is empty.
        The optional *label* is included in the error message for context.
        """
        if not self:
            ctx = f" for {label!r}" if label else ""
            raise ValueError(f"Expected at least 1 result{ctx}, found 0")
        name = next(iter(self))
        return name, self[name]

    def get_first_name(self, label: str = "") -> str:
        """Return the first member name. Raises ``ValueError`` if empty."""
        name, _ = self.get_first(label)
        return name

    def where(self, predicate: Callable[[_M], bool]) -> CollectResult[_M]:
        """Filter entries by a predicate on the value.

        Returns a new ``CollectResult`` containing only entries where
        ``predicate(value)`` returns ``True``.
        """
        return CollectResult({name: val for name, val in self.items() if predicate(val)})

    def sorted_by(self, attr: str, *, reverse: bool = False) -> list[tuple[str, _M]]:
        """Sort entries by a value attribute.

        Returns a list of ``(name, value)`` pairs sorted by the value of
        *attr* on each entry.

        Example::

            hooks = OnSave.collect_markers(cls).sorted_by("priority")
            for name, marker in hooks:
                getattr(instance, name)()
        """
        return sorted(self.items(), key=lambda pair: getattr(pair[1], attr), reverse=reverse)

    def names(self) -> list[str]:
        """Return all member names as a list."""
        return list(self.keys())

    def values_list(self) -> list[_M]:
        """Return all values as a list."""
        return list(self.values())


class MemberInfo:
    """Metadata about a single class member (field or method).

    Every member collected from a class (via ``.fields``, ``.methods``,
    ``.members``, or a marker descriptor) is represented as a ``MemberInfo``.

    Attributes:
        name (str): The member name (e.g. 'email', 'validate').
        kind (MemberKind): ``MemberKind.FIELD`` or ``MemberKind.METHOD``.
        type (type | None): The base type (unwrapped from ``Annotated``).
            ``None`` for methods.
        owner (type | None): The class that defined this member.
        default (Any): The default value, or ``MISSING`` if none.
        markers (list[MarkerInstance]): All markers attached to this member.

    Properties:
        is_field (bool): ``True`` if ``kind == MemberKind.FIELD``.
        is_method (bool): ``True`` if ``kind == MemberKind.METHOD``.
        has_default (bool): ``True`` if a default value exists (not ``MISSING``).

    Querying markers::

        info = User.fields["name"]

        info.has("required")          # True if marker is present
        info.get("max_length")        # MarkerInstance or None
        info.get("max_length").limit  # access validated params
        info.get_all("required")      # list of all matching MarkerInstances

    Methods:
        has(marker_name: str) -> bool:
            Check if a marker with the given name is present.
        get(marker_name: str) -> MarkerInstance | None:
            Get the first ``MarkerInstance`` matching the name, or ``None``.
        get_all(marker_name: str) -> list[MarkerInstance]:
            Get all ``MarkerInstance`` objects matching the name.
    """

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

    @staticmethod
    def _resolve_marker_name(marker: str | type) -> str:
        """Resolve a marker name from a string or Marker class."""
        if isinstance(marker, str):
            return marker
        # Accept a Marker class — extract its _mark_name
        mark_name: str | None = getattr(marker, "_mark_name", None)
        if mark_name is not None:
            return mark_name
        raise TypeError(f"Expected a string or Marker class, got {type(marker).__name__}")

    def has(self, marker: str | type) -> bool:
        """Check if a marker is present. Accepts a name or Marker class."""
        name = self._resolve_marker_name(marker)
        return any(m._marker_name == name for m in self.markers)

    def get(self, marker: str | type) -> MarkerInstance | None:
        """Get the first matching MarkerInstance, or None. Accepts a name or Marker class."""
        name = self._resolve_marker_name(marker)
        return next((m for m in self.markers if m._marker_name == name), None)

    def get_marker(self, marker: str | type) -> MarkerInstance:
        """Get the matching MarkerInstance, or raise ``KeyError``.

        Like ``.get()`` but raises ``KeyError`` instead of returning ``None``.
        Accepts a marker name string or a ``Marker`` class.
        """
        name = self._resolve_marker_name(marker)
        result = next((m for m in self.markers if m._marker_name == name), None)
        if result is None:
            raise KeyError(f"Member {self.name!r} has no marker {name!r}")
        return result

    def get_all(self, marker: str | type) -> list[MarkerInstance]:
        """Get all matching MarkerInstances. Accepts a name or Marker class."""
        name = self._resolve_marker_name(marker)
        return [m for m in self.markers if m._marker_name == name]

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
