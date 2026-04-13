"""markers - Lightweight class introspection toolkit for Python.

Define typed markers, annotate fields and methods with them, and collect
metadata via MRO-walking descriptors. Built on ``typing.Annotated`` and
pydantic for schema validation.

Workflow::

    1. Define markers by subclassing ``Marker`` (class body = pydantic schema)
    2. Bundle markers into a ``MarkerGroup`` to get a ``.mixin``
    3. Inherit from the mixin in your classes
    4. Query metadata via descriptors: ``.fields``, ``.methods``, ``.required``, etc.

Quick example::

    from typing import Annotated
    from markers import Marker, MarkerGroup

    class Required(Marker): pass
    class MaxLen(Marker):
        mark = "max_length"
        limit: int

    class Validation(MarkerGroup):
        Required = Required
        MaxLen = MaxLen

    class User(Validation.mixin):
        name: Annotated[str, Validation.Required(), Validation.MaxLen(limit=100)]
        email: Annotated[str, Validation.Required()]

    User.required                            # {'name': MemberInfo, 'email': MemberInfo}
    User.fields["name"].get("max_length").limit  # 100

Public API:
    Marker          Subclass to define markers (with optional pydantic schema).
    MarkerGroup     Subclass to bundle related markers into a .mixin.
    Registry        Subclass to track and query across all subclasses.

Supporting types:
    MarkerInstance  A validated marker usage. Access schema fields as attributes.
    MemberInfo      Metadata about a field or method. Use .has()/.get()/.get_all().
    MemberKind      Enum: FIELD or METHOD.
    MISSING         Sentinel for fields with no default value.
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
