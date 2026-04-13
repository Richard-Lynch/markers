"""
markers.registry - Registry base class for cross-subclass collection.

    class Entity(DB.mixin, Registry): ...
    class User(Entity): ...
    class Post(Entity): ...

    # List registered subclasses
    Entity.subclasses()  # [User, Post]

    # Per-class access (same as always)
    User.required        # {'name': MemberInfo, 'email': MemberInfo}

    # Cross-class access via .all — dict of lists, grouped by member name
    Entity.all.required  # {'name': [MemberInfo(owner=User)], 'email': [...], 'title': [...]}
    Entity.all.fields    # {'id': [MemberInfo(owner=User), MemberInfo(owner=Post)], ...}
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from markers._types import MemberInfo
from markers.core import collector
from markers.descriptors import BaseMixin

__all__ = ["Registry"]


class AllProxy:
    """Proxy that gathers members from all subclasses into ``dict[str, list[MemberInfo]]``.

    Each key is a member name. Each value is a list of MemberInfo from
    every subclass that defines that member — so you can see which
    classes contribute each field/method.

        Entity.all.fields
        # {'id': [MemberInfo(owner=User), MemberInfo(owner=Post)],
        #  'name': [MemberInfo(owner=User)],
        #  'title': [MemberInfo(owner=Post)], ...}

        Entity.all.required
        # {'name': [MemberInfo(owner=User)],
        #  'email': [MemberInfo(owner=User), MemberInfo(owner=Customer)], ...}
    """

    def __init__(self, registry_cls: type) -> None:
        self._cls = registry_cls

    def _gather(self, extractor: Any) -> dict[str, list[MemberInfo]]:
        result: dict[str, list[MemberInfo]] = defaultdict(list)
        registry: dict[str, type] = getattr(self._cls, "_registry", {})
        for sub in registry.values():
            for name, info in extractor(sub).items():
                result[name].append(info)
        return dict(result)

    @property
    def members(self) -> dict[str, list[MemberInfo]]:
        """All members from all subclasses."""
        return self._gather(collector.collect)

    @property
    def fields(self) -> dict[str, list[MemberInfo]]:
        """All fields from all subclasses."""
        return self._gather(collector.fields)

    @property
    def methods(self) -> dict[str, list[MemberInfo]]:
        """All methods from all subclasses."""
        return self._gather(collector.methods)

    def __getattr__(self, marker_name: str) -> dict[str, list[MemberInfo]]:
        """Collect a specific marker across all subclasses."""
        if marker_name.startswith("_"):
            raise AttributeError(marker_name)
        return self._gather(lambda sub: collector.filter(sub, marker_name))


class AllDescriptor:
    """Descriptor that returns an AllProxy bound to the registry class."""

    def __get__(self, obj: object, cls: type) -> AllProxy:
        return AllProxy(cls)


class Registry(BaseMixin):
    """Base class that tracks all subclasses.

    Inherits BaseMixin so ``fields``, ``methods``, and ``members``
    are always available.

    Per-class access works as usual::

        User.fields          # dict[str, MemberInfo]
        User.required        # dict[str, MemberInfo]

    Cross-class access via ``.all`` gathers into lists by member name::

        Entity.all.fields    # dict[str, list[MemberInfo]]
        Entity.all.required  # dict[str, list[MemberInfo]]

    Each list entry has ``.owner`` so you know which class it came from.

    Use ``subclasses()`` for direct iteration::

        for cls in Entity.subclasses():
            print(cls.__name__, list(cls.required.keys()))
    """

    _registry: dict[str, type] = {}
    all = AllDescriptor()

    def __init_subclass__(cls, abstract: bool = False, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not abstract:
            cls._registry = {}
            for base in cls.__mro__[1:]:
                if base is Registry:
                    break
                if issubclass(base, Registry) and hasattr(base, "_registry"):
                    base._registry[cls.__name__] = cls
                    break

    @classmethod
    def subclasses(cls) -> list[type]:
        """Return all registered subclasses."""
        return list(cls._registry.values())
