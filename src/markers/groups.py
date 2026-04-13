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

from typing import Any

from markers.descriptors import BaseMixin, BaseMixinMeta, MarkerDescriptor
from markers.marker import Marker, MarkerMeta

__all__ = ["MarkerGroup"]


class MarkerGroupMeta(type):
    """Metaclass that auto-builds a .mixin from Marker class attributes."""

    mixin: type[BaseMixin]
    _markers: dict[str, MarkerMeta]

    def __new__(mcs, name: str, bases: tuple, namespace: dict, **kwargs: Any) -> "MarkerGroupMeta":
        cls = super().__new__(mcs, name, bases, namespace)

        if name == "MarkerGroup":
            return cls

        # Find all Marker subclasses assigned as class attributes
        found_markers: dict[str, MarkerMeta] = {}

        # Support list-based syntax: markers = [Required, MaxLen]
        marker_list = namespace.get("markers")
        if isinstance(marker_list, (list, tuple)):
            for val in marker_list:
                if isinstance(val, type) and issubclass(val, Marker) and val is not Marker:
                    found_markers[val.__name__] = val  # type: ignore[assignment]

        # Also support attribute-based syntax: Required = Required
        for attr, val in namespace.items():
            if attr == "markers":
                continue
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

        cls.mixin = BaseMixinMeta(f"{name}Mixin", (BaseMixin,), mixin_attrs)  # type: ignore[assignment]
        cls._markers = found_markers
        return cls


class MarkerGroup(metaclass=MarkerGroupMeta):
    """Bundle related markers and produce a ``.mixin`` for model classes.

    This is how marker descriptors get onto your classes. Subclass and
    assign ``Marker`` subclasses as class attributes. The group auto-generates
    a ``.mixin`` class that provides:

    - A **marker descriptor** per marker (e.g. ``.primary_key``, ``.indexed``)
      that returns ``dict[str, MemberInfo]`` of members carrying that marker.
    - **``.fields``**, **``.methods``**, **``.members``** from ``BaseMixin``
      — always available on any class using at least one group mixin.

    Defining a group::

        class DB(MarkerGroup):
            PrimaryKey = PrimaryKey
            Indexed = Indexed
            ForeignKey = ForeignKey

    Using the mixin::

        class User(DB.mixin):
            id: Annotated[int, DB.PrimaryKey()]
            email: Annotated[str, DB.Indexed(unique=True)]

        User.primary_key  # {'id': MemberInfo(...)}
        User.indexed      # {'email': MemberInfo(...)}
        User.fields       # all fields

    Multiple group mixins compose naturally::

        class User(DB.mixin, Validation.mixin, Search.mixin):
            ...

    Groups inherit from other groups to compose marker sets::

        class FullDB(DB):
            Unique = Unique
            Check = Check

        # FullDB.mixin has all of DB's descriptors plus 'unique' and 'check'

    Type checking:
        ``.fields``, ``.methods``, and ``.members`` are fully typed as
        ``dict[str, MemberInfo]`` via ``BaseMixin``. Marker-specific
        descriptors (e.g. ``.primary_key``) are dynamic and not visible
        to type checkers. Two typed alternatives:

        - Use ``Marker.collect()``::

              PrimaryKey.collect(User)  # fully typed: dict[str, MemberInfo]

        - Add explicit ``ClassVar`` annotations::

              if TYPE_CHECKING:
                  primary_key: ClassVar[dict[str, MemberInfo]]

        Marker constructor parameters (e.g. ``MaxLen(limit=100)``) are
        fully validated by type checkers via ``dataclass_transform``.

    Attributes:
        mixin (type[BaseMixin]): The generated mixin class. Inherit from this.
        _markers (dict[str, MarkerMeta]): Mapping of attribute name to Marker class.
    """

    mixin: type[BaseMixin]
    _markers: dict[str, MarkerMeta] = {}

    @staticmethod
    def combine(*groups: type) -> type:
        """Create a single mixin combining multiple ``MarkerGroup`` mixins.

        Eliminates the need for multiple mixin inheritance (and the
        ``# type: ignore[misc]`` that comes with it)::

            # Instead of:
            class User(DB.mixin, Validation.mixin, Search.mixin):  # type: ignore[misc]
                ...

            # Write:
            AppMixin = MarkerGroup.combine(DB, Validation, Search)
            class User(AppMixin):
                ...

        The returned mixin carries all descriptors from all groups.
        """
        attrs: dict[str, Any] = {}
        for group in groups:
            markers: dict[str, MarkerMeta] = getattr(group, "_markers", {})
            for marker_cls in markers.values():
                mark_name = marker_cls._mark_name
                attrs[mark_name] = MarkerDescriptor(mark_name)
        names = "+".join(g.__name__ for g in groups)
        return BaseMixinMeta(f"Combined({names})", (BaseMixin,), attrs)
