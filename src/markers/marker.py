"""
markers.marker - Marker is both the schema and the factory.

Define markers by subclassing Marker. The class body IS the pydantic
schema. Calling the class creates a validated MarkerInstance.

    class Searchable(Marker):
        boost: float = 1.0
        analyzer: str = "standard"

    class Required(Marker):
        pass

Markers don't carry mixins — use MarkerGroup for that.

Intermediate base markers for shared schema fields::

    class LifecycleMarker(Marker):
        priority: int = 0

    class OnSave(LifecycleMarker):
        mark = "on_save"
"""

from __future__ import annotations

import sys
from typing import Any

from pydantic import BaseModel, ConfigDict

from markers._types import MarkerInstance, MemberInfo
from markers.core import collector

if sys.version_info >= (3, 14):
    import annotationlib


def _get_own_class_annotations(cls: type) -> dict[str, Any]:
    """Get annotations defined directly on *cls* (not inherited), as strings.

    On Python 3.14+ uses annotationlib.get_annotations with STRING format
    to avoid evaluating forward references. On older versions reads
    __annotations__ from the class __dict__.
    """
    if sys.version_info >= (3, 14):
        return annotationlib.get_annotations(cls, format=annotationlib.Format.STRING)
    return dict(vars(cls).get("__annotations__", {}))


__all__ = ["Marker"]

# Fields that belong to Marker infrastructure, not the schema
_MARKER_INTERNAL = {"mark", "collect", "invalidate"}


class MarkerMeta(type):
    """Metaclass that makes Marker subclasses act as schema + factory."""

    _mark_name: str
    _schema_model: type[BaseModel] | None
    _schema_annotations: dict[str, Any]
    _schema_defaults: dict[str, Any]

    def __new__(mcs, name: str, bases: tuple, namespace: dict, **kwargs: Any) -> type:
        # Don't process Marker base class itself
        if name == "Marker":
            return super().__new__(mcs, name, bases, namespace)

        # Determine marker name — only set if explicitly provided or this is a leaf
        mark_name = namespace.pop("mark", None)

        # Create the class first so annotations are accessible via the type
        # (on Python 3.14.4+ with PEP 749, annotations may not be in the
        # namespace dict at all — they're only available on the created class).
        cls = super().__new__(mcs, name, bases, namespace)

        # Collect schema annotations from this class AND parent markers
        schema_annotations: dict[str, Any] = {}
        schema_defaults: dict[str, Any] = {}

        # Walk bases for inherited schema fields
        for base in reversed(bases):
            if base is Marker:
                continue
            base_schema = getattr(base, "_schema_annotations", {})
            base_defaults = getattr(base, "_schema_defaults", {})
            schema_annotations.update(base_schema)
            schema_defaults.update(base_defaults)

        # Add this class's own annotations (read from the created class)
        own_annotations = _get_own_class_annotations(cls)
        for k, v in own_annotations.items():
            if k not in _MARKER_INTERNAL and not k.startswith("_"):
                schema_annotations[k] = v

        # Extract defaults from class vars
        for k in list(schema_annotations.keys()):
            if k in vars(cls):
                schema_defaults[k] = vars(cls)[k]
                # Remove from class dict so schema fields don't shadow descriptors
                try:
                    delattr(cls, k)
                except AttributeError:
                    pass

        # Build pydantic model if there are schema fields
        if schema_annotations:
            model_ns: dict[str, Any] = {
                "__annotations__": dict(schema_annotations),
                "model_config": ConfigDict(extra="forbid"),
            }
            model_ns.update(schema_defaults)
            schema_model = type(f"{name}Params", (BaseModel,), model_ns)
        else:
            schema_model = None

        # If no explicit mark name, default to lowercased class name
        if mark_name is None:
            mark_name = name.lower()

        cls._mark_name = mark_name
        cls._schema_model = schema_model
        cls._schema_annotations = schema_annotations
        cls._schema_defaults = schema_defaults

        return cls

    def __call__(cls, **kwargs: Any) -> MarkerInstance:
        """Create a validated MarkerInstance."""
        if cls is Marker:
            raise TypeError("Cannot instantiate Marker directly — subclass it")

        schema_model = cls._schema_model

        if schema_model is not None:
            params = schema_model(**kwargs)
            return MarkerInstance(cls._mark_name, params.model_dump(), params)
        else:
            if kwargs:
                raise TypeError(f"Marker '{cls._mark_name}' accepts no parameters, got: {set(kwargs.keys())}")
            return MarkerInstance(cls._mark_name, {})

    def __repr__(cls) -> str:
        if cls is Marker:
            return "<class 'Marker'>"
        if cls._schema_model is not None:
            return f"<Marker '{cls._mark_name}' schema={cls._schema_model.__name__}>"
        return f"<Marker '{cls._mark_name}'>"


class Marker(metaclass=MarkerMeta):
    """Base class for defining markers.

    Subclass to create a marker. The class body **is** the pydantic schema:
    typed fields become validated parameters. Leave empty for a schema-less
    marker (a simple tag with no parameters).

    Calling a Marker subclass returns a ``MarkerInstance`` with validated
    params. Use it as ``Annotated[]`` metadata or as a method decorator.

    Class attributes:
        mark (str, optional): Explicit marker name used for querying
            (e.g. ``User.required``). Defaults to the lowercased class name.

    Schema markers (with typed fields)::

        class MaxLen(Marker):
            mark = "max_length"   # queried as .max_length
            limit: int            # required param
            strict: bool = False  # optional param with default

        MaxLen(limit=100)         # -> MarkerInstance
        MaxLen()                  # ValidationError: 'limit' required
        MaxLen(limit=100, x=1)   # ValidationError: extra fields forbidden

    Schema-less markers (no params)::

        class Required(Marker): pass

        Required()       # -> MarkerInstance (empty)
        Required(x=1)   # TypeError: no parameters accepted

    As Annotated metadata::

        name: Annotated[str, Required(), MaxLen(limit=100)]

    As method decorator::

        @OnSave(priority=10)
        def validate(self): ...

    Intermediate bases share schema fields across related markers::

        class LifecycleMarker(Marker):
            priority: int = 0

        class OnSave(LifecycleMarker):
            mark = "on_save"

        class OnDelete(LifecycleMarker):
            mark = "on_delete"

        # Both have 'priority' with default 0, different mark names.

    Class methods:
        collect(cls, target):
            Collect all members carrying this marker from ``target``.
            Returns ``dict[str, MemberInfo]``.
            Must be called on a subclass, not ``Marker`` itself::

                Required.collect(User)  # {'name': MemberInfo, 'email': MemberInfo}

        invalidate(cls, target):
            Clear cached collection for ``target``. Useful after dynamic
            class modification. Can be called on any subclass or ``Marker``::

                Marker.invalidate(User)
    """

    _mark_name: str
    _schema_model: type[BaseModel] | None
    _schema_annotations: dict[str, Any]
    _schema_defaults: dict[str, Any]

    @classmethod
    def collect(cls, target: type) -> dict[str, MemberInfo]:
        """Collect all members carrying this marker from target class.

        Must be called on a concrete Marker subclass, not on Marker itself.
        """
        if cls is Marker:
            raise TypeError(
                "collect() must be called on a Marker subclass, e.g. Required.collect(User), not Marker.collect(User)"
            )
        return collector.filter(target, cls._mark_name)

    @classmethod
    def invalidate(cls, target: type) -> None:
        """Clear the cached collection for a target class.

        Can be called on any Marker subclass or on Marker itself —
        invalidation is not marker-specific, it clears the entire
        cache for the target class.
        """
        collector.invalidate(target)
