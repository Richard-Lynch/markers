"""
markers.core - Unified member collection and caching.
"""

from __future__ import annotations

import sys
import weakref
from typing import get_type_hints

from markers._types import MISSING, MarkerInstance, MemberInfo, MemberKind

# Python 3.14+ provides annotationlib with a proper get_annotations() that
# handles the deferred evaluation protocol (PEP 749). On older versions,
# fall back to reading __annotations__ directly.
if sys.version_info >= (3, 14):
    from annotationlib import get_annotations as _get_own_annotations
else:

    def _get_own_annotations(cls: type, **kwargs: object) -> dict[str, object]:  # type: ignore[misc]
        return getattr(cls, "__annotations__", {})


__all__: list[str] = []  # No public API — use Marker/Registry instead


class Collector:
    """Walks a class's MRO once, collects all members (fields + methods),
    and caches the result per-class using weak references.

    Not part of the public API. Access via Marker.collect / Marker.invalidate.
    """

    def __init__(self) -> None:
        self._cache: dict[int, dict[str, MemberInfo]] = {}
        self._refs: dict[int, weakref.ref[type]] = {}

    def _cleanup(self, cls_id: int) -> None:
        self._cache.pop(cls_id, None)
        self._refs.pop(cls_id, None)

    def collect(self, cls: type) -> dict[str, MemberInfo]:
        cls_id = id(cls)

        # Check cache — verify the weakref is still alive
        if cls_id in self._cache:
            ref = self._refs.get(cls_id)
            if ref is not None and ref() is not None:
                return self._cache[cls_id]
            else:
                self._cleanup(cls_id)

        members: dict[str, MemberInfo] = {}

        for klass in reversed(cls.__mro__):
            if klass is object:
                continue

            # --- Fields from annotations ---
            try:
                hints = get_type_hints(klass, include_extras=True)
            except Exception:
                hints = _get_own_annotations(klass)

            own_names = set(_get_own_annotations(klass).keys())
            for name in own_names:
                if name.startswith("_"):
                    continue
                hint = hints.get(name)
                if hint is None:
                    continue
                if hasattr(hint, "__metadata__"):
                    base_type = hint.__args__[0]
                    markers = [m for m in hint.__metadata__ if isinstance(m, MarkerInstance)]
                else:
                    base_type = hint
                    markers = []
                default = vars(klass).get(name, MISSING)
                members[name] = MemberInfo(
                    name=name,
                    kind=MemberKind.FIELD,
                    type_=base_type,
                    markers=markers,
                    default=default,
                    owner=klass,
                )

            # --- Methods with _markers ---
            for attr, val in vars(klass).items():
                method_markers: list[MarkerInstance] | None = getattr(val, "_markers", None)
                if method_markers:
                    members[attr] = MemberInfo(
                        name=attr,
                        kind=MemberKind.METHOD,
                        markers=list(method_markers),
                        owner=klass,
                    )

        self._cache[cls_id] = members

        # Store weakref for cache invalidation on GC.
        # If weakref creation fails (e.g. some C extension types),
        # cache without auto-cleanup — manual invalidate() still works.
        def _weak_callback(ref: weakref.ref[type], cid: int = cls_id) -> None:
            self._cleanup(cid)

        try:
            self._refs[cls_id] = weakref.ref(cls, _weak_callback)
        except TypeError:
            # Can't weakref this type — cache persists until manual invalidate()
            pass

        return members

    def invalidate(self, cls: type) -> None:
        """Clear the cached collection for a class."""
        self._cleanup(id(cls))

    def filter(self, cls: type, marker_name: str) -> dict[str, MemberInfo]:
        """Collect and return only members carrying a specific marker."""
        return {n: m for n, m in self.collect(cls).items() if m.has(marker_name)}

    def fields(self, cls: type) -> dict[str, MemberInfo]:
        """Collect and return only field members."""
        return {n: m for n, m in self.collect(cls).items() if m.kind == MemberKind.FIELD}

    def methods(self, cls: type) -> dict[str, MemberInfo]:
        """Collect and return only method members."""
        return {n: m for n, m in self.collect(cls).items() if m.kind == MemberKind.METHOD}


collector = Collector()
