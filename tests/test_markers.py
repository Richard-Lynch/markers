"""
Tests for markers.

Run with: pytest tests/ -v
"""

from typing import Annotated

import pytest

from markers import MISSING, CollectResult, Marker, MarkerGroup, MemberInfo, MemberKind, Registry
from markers.core import collector

# ===================================================================
# Fixtures — define markers and groups
# ===================================================================


class Required(Marker):
    pass


class Unique(Marker):
    pass


class MaxLen(Marker):
    mark = "max_length"
    limit: int


class Searchable(Marker):
    boost: float = 1.0
    analyzer: str = "standard"


class Range(Marker):
    min: float
    max: float


class ForeignKey(Marker):
    mark = "foreign_key"
    table: str
    column: str
    on_delete: str = "CASCADE"


class PrimaryKey(Marker):
    mark = "primary_key"
    auto_increment: bool = True


class Indexed(Marker):
    unique: bool = False


class LifecycleMarker(Marker):
    priority: int = 0


class OnSave(LifecycleMarker):
    mark = "on_save"


class OnDelete(LifecycleMarker):
    mark = "on_delete"


class DB(MarkerGroup):
    PrimaryKey = PrimaryKey
    Indexed = Indexed
    Unique = Unique
    ForeignKey = ForeignKey


class Search(MarkerGroup):
    Searchable = Searchable


class Validation(MarkerGroup):
    Required = Required
    MaxLen = MaxLen
    Range = Range


class Lifecycle(MarkerGroup):
    OnSave = OnSave
    OnDelete = OnDelete


# State machine markers for CollectResult tests


class _SMState(Marker):
    mark = "state"
    initial: bool = False
    final: bool = False


class _SMTransition(Marker):
    mark = "transition"
    source: list
    target: str


class _SM(MarkerGroup):
    State = _SMState
    Transition = _SMTransition


class _SMachine(_SM.mixin):
    idle: Annotated[str, _SM.State(initial=True)]
    running: Annotated[str, _SM.State()]
    done: Annotated[str, _SM.State(final=True)]


class _SMachineNoInitial(_SM.mixin):
    idle: Annotated[str, _SM.State()]
    running: Annotated[str, _SM.State()]


class _SMachineFull(_SM.mixin):
    idle: Annotated[str, _SM.State(initial=True)]
    running: Annotated[str, _SM.State()]
    done: Annotated[str, _SM.State(final=True)]
    error: Annotated[str, _SM.State(final=True)]

    @_SM.Transition(source=["idle"], target="running")
    def start(self):
        pass

    @_SM.Transition(source=["running"], target="done")
    def finish(self):
        pass

    @_SM.Transition(source=["running"], target="error")
    def fail(self):
        pass


# ===================================================================
# Marker definition
# ===================================================================


class TestMarkerDefinition:
    def test_schema_less_marker_has_no_schema_model(self):
        assert Required._schema_model is None
        assert Required._mark_name == "required"

    def test_schema_marker_builds_pydantic_model(self):
        assert MaxLen._schema_model is not None
        assert MaxLen._mark_name == "max_length"

    def test_explicit_mark_name(self):
        assert ForeignKey._mark_name == "foreign_key"

    def test_default_mark_name_is_lowercased_class_name(self):
        assert Searchable._mark_name == "searchable"
        assert Required._mark_name == "required"

    def test_intermediate_base_inherits_schema_fields(self):
        assert "priority" in OnSave._schema_annotations
        assert "priority" in OnDelete._schema_annotations
        assert OnSave._mark_name == "on_save"
        assert OnDelete._mark_name == "on_delete"

    def test_repr_for_schema_less(self):
        assert "required" in repr(Required)

    def test_repr_for_schema(self):
        r = repr(Searchable)
        assert "searchable" in r
        assert "SearchableParams" in r


# ===================================================================
# MarkerInstance creation
# ===================================================================


class TestMarkerInstanceCreation:
    def test_schema_less_creates_empty_instance(self):
        inst = Required()
        assert inst.marker_name == "required"
        assert inst._kwargs == {}
        assert inst._params is None

    def test_schema_validates_and_stores_params(self):
        inst = MaxLen(limit=100)
        assert inst.marker_name == "max_length"
        assert inst._kwargs == {"limit": 100}
        assert inst._params is not None
        assert inst.limit == 100

    def test_schema_defaults_applied(self):
        inst = Searchable()
        assert inst.boost == 1.0
        assert inst.analyzer == "standard"

    def test_schema_defaults_overridden(self):
        inst = Searchable(boost=3.0)
        assert inst.boost == 3.0
        assert inst.analyzer == "standard"

    def test_schema_less_rejects_kwargs(self):
        with pytest.raises(TypeError):
            Required(oops=True)

    def test_schema_rejects_missing_required(self):
        with pytest.raises(Exception):
            MaxLen()

    def test_schema_rejects_wrong_type(self):
        with pytest.raises(Exception):
            MaxLen(limit="nope")

    def test_schema_rejects_unknown_field(self):
        with pytest.raises(Exception):
            MaxLen(limit=100, extra=True)

    def test_cannot_instantiate_marker_base(self):
        with pytest.raises(TypeError):
            Marker()

    def test_inherited_schema_fields_work(self):
        inst = OnSave(priority=5)
        assert inst.priority == 5

    def test_inherited_schema_defaults_work(self):
        inst = OnSave()
        assert inst.priority == 0

    def test_int_coerced_to_float_in_range(self):
        inst = Range(min=0, max=100)
        assert inst.min == 0
        assert inst.max == 100


# ===================================================================
# MarkerInstance as decorator
# ===================================================================


class TestMarkerInstanceDecorator:
    def test_decorating_attaches_markers(self):
        inst = OnSave(priority=1)

        def fn():
            pass

        result = inst(fn)
        assert result is fn
        assert hasattr(fn, "_markers")
        assert len(fn._markers) == 1
        assert fn._markers[0] is inst

    def test_multiple_decorators_stack(self):
        def fn():
            pass

        OnSave(priority=1)(fn)
        OnDelete()(fn)
        assert len(fn._markers) == 2

    def test_decorating_copies_list_to_avoid_sharing(self):
        def fn1():
            pass

        def fn2():
            pass

        OnSave()(fn1)
        OnSave()(fn2)
        assert fn1._markers is not fn2._markers


# ===================================================================
# MarkerInstance attribute access
# ===================================================================


class TestMarkerInstanceAttributes:
    def test_attribute_access_on_schema_instance(self):
        inst = Searchable(boost=2.5)
        assert inst.boost == 2.5
        assert inst.analyzer == "standard"

    def test_attribute_access_raises_on_missing(self):
        inst = Required()
        with pytest.raises(AttributeError):
            inst.nonexistent

    def test_repr_for_schema_instance(self):
        inst = MaxLen(limit=100)
        assert "limit=100" in repr(inst)

    def test_repr_for_schema_less_instance(self):
        inst = Required()
        assert repr(inst) == "required()"

    def test_as_dict_with_schema(self):
        inst = Searchable(boost=2.5)
        d = inst.as_dict()
        assert d == {"boost": 2.5, "analyzer": "standard"}

    def test_as_dict_without_schema(self):
        inst = Required()
        assert inst.as_dict() == {}

    def test_eq_same_marker_same_params(self):
        assert MaxLen(limit=100) == MaxLen(limit=100)

    def test_eq_same_marker_different_params(self):
        assert MaxLen(limit=100) != MaxLen(limit=200)

    def test_eq_different_marker(self):
        assert Required() != Unique()

    def test_eq_not_marker_instance(self):
        assert Required() != "required"

    def test_not_hashable(self):
        with pytest.raises(TypeError):
            hash(Required())


# ===================================================================
# MarkerGroup
# ===================================================================


class TestMarkerGroup:
    def test_group_collects_markers(self):
        assert "PrimaryKey" in DB._markers
        assert "Indexed" in DB._markers
        assert "Unique" in DB._markers
        assert "ForeignKey" in DB._markers

    def test_group_builds_mixin_with_descriptors(self):
        mixin = DB.mixin
        assert hasattr(mixin, "primary_key")
        assert hasattr(mixin, "indexed")

    def test_group_mixin_inherits_basemixin(self):
        class M(DB.mixin):
            id: Annotated[int, DB.PrimaryKey()]

        assert hasattr(M, "fields")
        assert hasattr(M, "methods")
        assert hasattr(M, "members")

    def test_group_inheritance_composes_markers(self):
        class BaseGroup(MarkerGroup):
            Required = Required

        class ExtendedGroup(BaseGroup):
            MaxLen = MaxLen

        assert "Required" in ExtendedGroup._markers
        assert "MaxLen" in ExtendedGroup._markers

    def test_access_markers_via_group(self):
        assert DB.PrimaryKey is PrimaryKey
        inst = DB.PrimaryKey()
        assert inst.marker_name == "primary_key"


# ===================================================================
# Collection — fields
# ===================================================================


class TestCollectionFields:
    def test_plain_field_collected(self):
        class M(DB.mixin):
            age: int = 0

        collector.invalidate(M)
        assert "age" in M.fields
        info = M.fields["age"]
        assert info.is_field
        assert info.type is int
        assert info.has_default
        assert info.default == 0

    def test_annotated_field_collected_with_markers(self):
        class M(DB.mixin, Validation.mixin):
            name: Annotated[str, Validation.Required(), Validation.MaxLen(limit=100)]

        collector.invalidate(M)
        info = M.fields["name"]
        assert info.has("required")
        assert info.has("max_length")
        assert info.get("max_length").limit == 100

    def test_field_without_default(self):
        class M(DB.mixin):
            name: str

        collector.invalidate(M)
        info = M.fields["name"]
        assert not info.has_default
        assert info.default is MISSING

    def test_field_owner_tracked(self):
        class Mixin:
            x: int = 1

        class M(Mixin, DB.mixin):
            y: int = 2

        collector.invalidate(M)
        assert M.fields["x"].owner is Mixin
        assert M.fields["y"].owner is M

    def test_private_fields_skipped(self):
        class M(DB.mixin):
            _internal: int = 0
            public: int = 1

        collector.invalidate(M)
        assert "_internal" not in M.fields
        assert "public" in M.fields

    def test_mixin_fields_inherited_through_mro(self):
        class TimeMixin:
            created_at: Annotated[str, DB.Indexed()]

        class M(TimeMixin, DB.mixin):
            name: str

        collector.invalidate(M)
        assert "created_at" in M.fields
        assert "name" in M.fields


# ===================================================================
# Collection — methods
# ===================================================================


class TestCollectionMethods:
    def test_decorated_method_collected(self):
        class M(Lifecycle.mixin):
            @OnSave(priority=10)
            def validate(self):
                pass

        collector.invalidate(M)
        assert "validate" in M.methods
        info = M.methods["validate"]
        assert info.is_method
        assert info.has("on_save")
        assert info.get("on_save").priority == 10

    def test_inherited_decorated_methods_collected(self):
        class Base(Lifecycle.mixin):
            @OnSave()
            def base_hook(self):
                pass

        class Child(Base):
            @OnSave(priority=5)
            def child_hook(self):
                pass

        collector.invalidate(Child)
        assert "base_hook" in Child.methods
        assert "child_hook" in Child.methods

    def test_method_owner_tracked(self):
        class Base(Lifecycle.mixin):
            @OnSave()
            def hook(self):
                pass

        class Child(Base):
            pass

        collector.invalidate(Child)
        assert Child.methods["hook"].owner is Base

    def test_classmethod_with_marker_collected(self):
        class M(Lifecycle.mixin):
            @OnSave(priority=5)
            @classmethod
            def cls_hook(cls):
                pass

        collector.invalidate(M)
        assert "cls_hook" in M.methods
        assert M.methods["cls_hook"].get("on_save").priority == 5

    def test_staticmethod_with_marker_collected(self):
        class M(Lifecycle.mixin):
            @OnSave(priority=3)
            @staticmethod
            def static_hook():
                pass

        collector.invalidate(M)
        assert "static_hook" in M.methods
        assert M.methods["static_hook"].get("on_save").priority == 3

    def test_marker_then_classmethod_collected(self):
        """Marker applied before @classmethod (outer decorator)."""

        class M(Lifecycle.mixin):
            @classmethod
            @OnSave(priority=7)
            def hook(cls):
                pass

        collector.invalidate(M)
        assert "hook" in M.methods
        assert M.methods["hook"].get("on_save").priority == 7


# ===================================================================
# Collection — marker filtering
# ===================================================================


class TestMarkerFiltering:
    def test_marker_descriptor_filters_correctly(self):
        class M(DB.mixin, Validation.mixin, Search.mixin):
            id: Annotated[int, DB.PrimaryKey()]
            name: Annotated[str, Validation.Required(), Search.Searchable()]
            age: int = 0

        collector.invalidate(M)
        assert list(M.primary_key.keys()) == ["id"]
        assert "name" in M.required
        assert "name" in M.searchable
        assert "age" not in M.required

    def test_marker_collect_works_imperatively(self):
        class M(DB.mixin, Validation.mixin):
            name: Annotated[str, Validation.Required()]
            age: int = 0

        collector.invalidate(M)
        result = Required.collect(M)
        assert "name" in result
        assert "age" not in result

    def test_marker_collect_guard_on_base_class(self):
        with pytest.raises(TypeError, match="Marker subclass"):
            Marker.collect(object)


# ===================================================================
# Collection — mixed fields and methods
# ===================================================================


class TestCollectionMixed:
    def test_members_includes_both_fields_and_methods(self):
        class M(DB.mixin, Lifecycle.mixin):
            id: Annotated[int, DB.PrimaryKey()]

            @OnSave()
            def hook(self):
                pass

        collector.invalidate(M)
        assert "id" in M.members
        assert "hook" in M.members
        assert M.members["id"].is_field
        assert M.members["hook"].is_method

    def test_fields_excludes_methods(self):
        class M(DB.mixin, Lifecycle.mixin):
            id: Annotated[int, DB.PrimaryKey()]

            @OnSave()
            def hook(self):
                pass

        collector.invalidate(M)
        assert "id" in M.fields
        assert "hook" not in M.fields

    def test_methods_excludes_fields(self):
        class M(DB.mixin, Lifecycle.mixin):
            id: Annotated[int, DB.PrimaryKey()]

            @OnSave()
            def hook(self):
                pass

        collector.invalidate(M)
        assert "hook" in M.methods
        assert "id" not in M.methods


# ===================================================================
# Cache
# ===================================================================


class TestCache:
    def test_cache_returns_same_result_on_second_call(self):
        class M(DB.mixin):
            x: int = 1

        collector.invalidate(M)
        r1 = collector.collect(M)
        r2 = collector.collect(M)
        assert r1 is r2

    def test_invalidate_clears_cache(self):
        class M(DB.mixin):
            x: int = 1

        collector.invalidate(M)
        r1 = collector.collect(M)
        collector.invalidate(M)
        r2 = collector.collect(M)
        assert r1 is not r2

    def test_marker_invalidate_works(self):
        class M(DB.mixin):
            x: int = 1

        collector.invalidate(M)
        r1 = collector.collect(M)
        Marker.invalidate(M)
        r2 = collector.collect(M)
        assert r1 is not r2


# ===================================================================
# MemberInfo
# ===================================================================


class TestMemberInfo:
    def test_has_get_get_all_work(self):
        inst1 = Required()
        inst2 = MaxLen(limit=50)
        info = MemberInfo(name="x", kind=MemberKind.FIELD, markers=[inst1, inst2])
        assert info.has("required")
        assert info.has("max_length")
        assert not info.has("nonexistent")
        assert info.get("required") is inst1
        assert info.get("max_length") is inst2
        assert info.get("nonexistent") is None
        assert info.get_all("required") == [inst1]

    def test_is_field_is_method(self):
        f = MemberInfo(name="x", kind=MemberKind.FIELD, markers=[])
        m = MemberInfo(name="y", kind=MemberKind.METHOD, markers=[])
        assert f.is_field and not f.is_method
        assert m.is_method and not m.is_field

    def test_has_default_and_missing(self):
        with_default = MemberInfo(name="x", kind=MemberKind.FIELD, markers=[], default=42)
        without = MemberInfo(name="y", kind=MemberKind.FIELD, markers=[])
        none_default = MemberInfo(name="z", kind=MemberKind.FIELD, markers=[], default=None)
        assert with_default.has_default and with_default.default == 42
        assert not without.has_default
        assert none_default.has_default and none_default.default is None


# ===================================================================
# Registry
# ===================================================================


class TestRegistry:
    def test_subclasses_registered(self):
        class Base(DB.mixin, Validation.mixin, Registry):
            id: Annotated[int, DB.PrimaryKey()]

        class A(Base):
            name: Annotated[str, Validation.Required()]

        class B(Base):
            title: Annotated[str, Validation.Required()]

        subs = Base.subclasses()
        assert len(subs) == 2
        assert A in subs
        assert B in subs

    def test_subclass_has_its_own_registry(self):
        class Base(Registry):
            pass

        class A(Base):
            pass

        class B(Base):
            pass

        assert A not in A.subclasses()
        assert B not in B.subclasses()

    def test_registry_inherits_basemixin(self):
        class Base(Registry):
            x: int = 1

        assert hasattr(Base, "fields")
        assert "x" in Base.fields

    def test_all_fields_gathers_from_all_subclasses(self):
        class Base(DB.mixin, Registry):
            id: Annotated[int, DB.PrimaryKey()]

        class A(Base):
            name: str

        class B(Base):
            title: str

        all_fields = Base.all.fields
        assert "name" in all_fields
        assert "title" in all_fields
        assert "id" in all_fields
        assert len(all_fields["id"]) == 2

    def test_all_required_gathers_marker_filtered(self):
        class Base(DB.mixin, Validation.mixin, Registry):
            id: Annotated[int, DB.PrimaryKey()]

        class A(Base):
            name: Annotated[str, Validation.Required()]

        class B(Base):
            title: Annotated[str, Validation.Required()]
            optional: str = ""

        all_req = Base.all.required
        assert "name" in all_req
        assert "title" in all_req
        assert "optional" not in all_req

    def test_all_methods_gathers_methods(self):
        class Base(Lifecycle.mixin, Registry):
            pass

        class A(Base):
            @OnSave()
            def hook_a(self):
                pass

        class B(Base):
            @OnSave()
            def hook_b(self):
                pass

        all_methods = Base.all.methods
        assert "hook_a" in all_methods
        assert "hook_b" in all_methods

    def test_all_preserves_owner(self):
        class Base(Validation.mixin, Registry):
            pass

        class A(Base):
            name: Annotated[str, Validation.Required()]

        class B(Base):
            name: Annotated[str, Validation.Required()]

        all_req = Base.all.required
        assert "name" in all_req
        owners = {info.owner for info in all_req["name"]}
        assert A in owners
        assert B in owners

    def test_subclasses_for_direct_iteration(self):
        class Base(Validation.mixin, Registry):
            pass

        class A(Base):
            x: Annotated[str, Validation.Required()]

        class B(Base):
            y: Annotated[str, Validation.Required()]

        names = {}
        for cls in Base.subclasses():
            names[cls.__name__] = list(cls.required.keys())
        assert names == {"A": ["x"], "B": ["y"]}

    def test_abstract_intermediate_falls_through(self):
        class Base(Registry):
            pass

        class Middle(Base, abstract=True):
            pass

        class Leaf(Middle):
            pass

        assert Leaf in Base.subclasses()
        assert not hasattr(Middle, "_registry") or "_registry" not in vars(Middle)

    def test_multiple_registry_bases(self):
        class RegA(Registry):
            pass

        class RegB(Registry):
            pass

        class Both(RegA, RegB):
            pass

        assert Both in RegA.subclasses()
        assert Both in RegB.subclasses()

    def test_all_proxy_repr(self):
        class Base(Registry):
            pass

        class _Sub1(Base):
            pass

        class _Sub2(Base):
            pass

        proxy = Base.all
        r = repr(proxy)
        assert "Base" in r
        assert "2 subclasses" in r

    def test_collect_rejects_instance(self):
        with pytest.raises(TypeError, match="expects a class"):
            Required.collect("not a class")  # type: ignore[arg-type]

    def test_collect_markers_rejects_instance(self):
        with pytest.raises(TypeError, match="expects a class"):
            Required.collect_markers("not a class")  # type: ignore[arg-type]


# ===================================================================
# Multiple groups
# ===================================================================


class TestMultipleGroups:
    def test_multiple_group_mixins_compose(self):
        class M(DB.mixin, Search.mixin, Validation.mixin, Lifecycle.mixin):
            id: Annotated[int, DB.PrimaryKey()]
            name: Annotated[str, Validation.Required(), Search.Searchable(boost=2.0)]

            @OnSave(priority=1)
            def hook(self):
                pass

        collector.invalidate(M)
        assert "id" in M.primary_key
        assert "name" in M.required
        assert "name" in M.searchable
        assert "hook" in M.on_save
        assert M.fields["name"].get("searchable").boost == 2.0
        assert M.methods["hook"].get("on_save").priority == 1


# ===================================================================
# Edge cases
# ===================================================================


class TestEdgeCases:
    def test_empty_class_has_no_fields_or_methods(self):
        class M(DB.mixin):
            pass

        collector.invalidate(M)
        assert M.fields == {}
        assert M.methods == {}

    def test_class_with_only_plain_type_hint_no_markers(self):
        class M(DB.mixin):
            age: int = 0

        collector.invalidate(M)
        info = M.fields["age"]
        assert info.markers == []
        assert not info.has("anything")

    def test_diamond_inheritance_works(self):
        class A:
            x: Annotated[str, Validation.Required()]

        class B(A):
            pass

        class C(A):
            pass

        class D(B, C, Validation.mixin):
            pass

        collector.invalidate(D)
        assert "x" in D.required

    def test_subclass_can_override_parent_field(self):
        class Parent(Validation.mixin):
            name: Annotated[str, Validation.Required()]

        class Child(Parent):
            name: Annotated[str, Validation.Required(), Validation.MaxLen(limit=50)]

        collector.invalidate(Child)
        info = Child.fields["name"]
        assert info.owner is Child
        assert info.has("max_length")


# ===================================================================
# Slot collision prevention
# ===================================================================


class TestSlotCollisionPrevention:
    def test_schema_field_name_no_collision(self):
        class Named(Marker):
            name: str

        inst = Named(name="my_table")
        assert inst.name == "my_table"
        assert inst.marker_name == "named"

    def test_schema_field_params_no_collision(self):
        class WithParams(Marker):
            params: str

        inst = WithParams(params="some_value")
        assert inst.params == "some_value"
        assert inst.marker_name == "withparams"

    def test_schema_field_kwargs_no_collision(self):
        class WithKwargs(Marker):
            kwargs: str

        inst = WithKwargs(kwargs="test")
        assert inst.kwargs == "test"
        assert inst.marker_name == "withkwargs"

    def test_marker_name_property_accessible(self):
        inst = Required()
        assert inst.marker_name == "required"
        inst2 = MaxLen(limit=10)
        assert inst2.marker_name == "max_length"

    def test_schema_field_name_in_annotated_collection(self):
        class _TableName(Marker):
            mark = "table_name"
            name: str

        class _TN(MarkerGroup):
            TableName = _TableName

        class _M(_TN.mixin):
            x: Annotated[str, _TableName(name="my_table")]

        collector.invalidate(_M)
        info = _M.table_name["x"]
        assert info.get("table_name").name == "my_table"


# ===================================================================
# MemberInfo.get_marker
# ===================================================================


class TestMemberInfoGetMarker:
    def test_get_marker_returns_instance(self):
        inst = Required()
        info = MemberInfo(name="x", kind=MemberKind.FIELD, markers=[inst])
        assert info.get_marker("required") is inst

    def test_get_marker_raises_on_missing(self):
        info = MemberInfo(name="x", kind=MemberKind.FIELD, markers=[Required()])
        with pytest.raises(KeyError, match="max_length"):
            info.get_marker("max_length")

    def test_get_marker_raises_on_empty_markers(self):
        info = MemberInfo(name="x", kind=MemberKind.FIELD, markers=[])
        with pytest.raises(KeyError, match="required"):
            info.get_marker("required")

    def test_get_marker_with_schema_params(self):
        inst = MaxLen(limit=50)
        info = MemberInfo(name="x", kind=MemberKind.FIELD, markers=[inst])
        marker = info.get_marker("max_length")
        assert marker.limit == 50

    def test_has_accepts_marker_class(self):
        info = MemberInfo(name="x", kind=MemberKind.FIELD, markers=[Required()])
        assert info.has(Required) is True
        assert info.has(MaxLen) is False

    def test_get_accepts_marker_class(self):
        inst = MaxLen(limit=50)
        info = MemberInfo(name="x", kind=MemberKind.FIELD, markers=[inst])
        assert info.get(MaxLen) is inst
        assert info.get(Required) is None

    def test_get_marker_accepts_marker_class(self):
        inst = Required()
        info = MemberInfo(name="x", kind=MemberKind.FIELD, markers=[inst])
        assert info.get_marker(Required) is inst
        with pytest.raises(KeyError):
            info.get_marker(MaxLen)

    def test_get_all_accepts_marker_class(self):
        inst = Required()
        info = MemberInfo(name="x", kind=MemberKind.FIELD, markers=[inst])
        assert info.get_all(Required) == [inst]
        assert info.get_all(MaxLen) == []


# ===================================================================
# collect_markers
# ===================================================================


class TestCollectMarkers:
    def test_returns_collect_result(self):
        class M(DB.mixin, Validation.mixin):
            name: Annotated[str, Validation.Required()]
            age: int = 0

        collector.invalidate(M)
        result = Required.collect_markers(M)
        assert isinstance(result, CollectResult)

    def test_returns_marker_instances_not_member_info(self):
        class M(DB.mixin, Validation.mixin):
            name: Annotated[str, Validation.Required(), Validation.MaxLen(limit=100)]

        collector.invalidate(M)
        result = Required.collect_markers(M)
        assert "name" in result
        # Value is MarkerInstance, not MemberInfo
        marker = result["name"]
        assert marker.marker_name == "required"

    def test_schema_params_accessible_directly(self):
        class M(Search.mixin):
            name: Annotated[str, Search.Searchable(boost=2.5)]

        collector.invalidate(M)
        result = Searchable.collect_markers(M)
        assert result["name"].boost == 2.5
        assert result["name"].analyzer == "standard"

    def test_only_matching_marker_returned(self):
        class M(DB.mixin, Validation.mixin):
            id: Annotated[int, DB.PrimaryKey()]
            name: Annotated[str, Validation.Required()]

        collector.invalidate(M)
        result = Required.collect_markers(M)
        assert "name" in result
        assert "id" not in result

    def test_guard_on_base_marker(self):
        with pytest.raises(TypeError, match="Marker subclass"):
            Marker.collect_markers(object)

    def test_empty_result_when_no_matches(self):
        class M(DB.mixin):
            id: Annotated[int, DB.PrimaryKey()]

        collector.invalidate(M)
        result = Required.collect_markers(M)
        assert len(result) == 0

    def test_methods_included(self):
        class M(Lifecycle.mixin):
            @OnSave(priority=10)
            def hook(self):
                pass

        collector.invalidate(M)
        result = OnSave.collect_markers(M)
        assert "hook" in result
        assert result["hook"].priority == 10


# ===================================================================
# CollectResult
# ===================================================================


class TestCollectResult:
    def test_get_one_with_single_entry(self):
        class M(DB.mixin, Validation.mixin):
            name: Annotated[str, Validation.Required()]

        collector.invalidate(M)
        result = Required.collect_markers(M)
        name, marker = result.get_one()
        assert name == "name"
        assert marker.marker_name == "required"

    def test_get_one_raises_on_empty(self):
        result = CollectResult()
        with pytest.raises(ValueError, match="Expected exactly 1"):
            result.get_one()

    def test_get_one_raises_on_multiple(self):
        class M(Validation.mixin):
            name: Annotated[str, Validation.Required()]
            email: Annotated[str, Validation.Required()]

        collector.invalidate(M)
        result = Required.collect_markers(M)
        with pytest.raises(ValueError, match="Expected exactly 1"):
            result.get_one()

    def test_get_one_label_in_error(self):
        result = CollectResult()
        with pytest.raises(ValueError, match="initial"):
            result.get_one(label="initial")

    def test_get_first_returns_first(self):
        class M(Validation.mixin):
            name: Annotated[str, Validation.Required()]
            email: Annotated[str, Validation.Required()]

        collector.invalidate(M)
        result = Required.collect_markers(M)
        name, _marker = result.get_first()
        assert name in result

    def test_get_first_raises_on_empty(self):
        result = CollectResult()
        with pytest.raises(ValueError, match="Expected at least 1"):
            result.get_first()

    def test_get_first_label_in_error(self):
        result = CollectResult()
        with pytest.raises(ValueError, match="final"):
            result.get_first(label="final")

    def test_get_one_name(self):
        class M(Validation.mixin):
            name: Annotated[str, Validation.Required()]

        collector.invalidate(M)
        result = Required.collect_markers(M)
        assert result.get_one_name() == "name"

    def test_get_first_name(self):
        class M(Validation.mixin):
            name: Annotated[str, Validation.Required()]
            email: Annotated[str, Validation.Required()]

        collector.invalidate(M)
        result = Required.collect_markers(M)
        assert result.get_first_name() in result

    def test_get_one_truncates_large_key_list(self):
        # Build a CollectResult with 15 entries
        result = CollectResult({f"field_{i}": Required() for i in range(15)})
        with pytest.raises(ValueError, match="5 more"):
            result.get_one()

    def test_sorted_by(self):
        collector.invalidate(_SMachineFull)
        transitions = _SMTransition.collect_markers(_SMachineFull)
        # Transitions have a 'target' attribute
        sorted_items = transitions.sorted_by("target")
        targets = [marker.target for _, marker in sorted_items]
        assert targets == sorted(targets)

    def test_sorted_by_reverse(self):
        collector.invalidate(_SMachineFull)
        transitions = _SMTransition.collect_markers(_SMachineFull)
        sorted_items = transitions.sorted_by("target", reverse=True)
        targets = [marker.target for _, marker in sorted_items]
        assert targets == sorted(targets, reverse=True)

    def test_where_filters_by_predicate(self):
        all_states = _SMState.collect_markers(_SMachine)
        assert len(all_states) == 3

        initials = all_states.where(lambda m: m.initial)
        assert isinstance(initials, CollectResult)
        assert len(initials) == 1
        assert "idle" in initials

        finals = all_states.where(lambda m: m.final)
        assert len(finals) == 1
        assert "done" in finals

        neither = all_states.where(lambda m: not m.initial and not m.final)
        assert len(neither) == 1
        assert "running" in neither

    def test_where_chained_with_get_one(self):
        name, marker = _SMState.collect_markers(_SMachine).where(lambda m: m.initial).get_one()
        assert name == "idle"
        assert marker.initial is True

    def test_names_method(self):
        class M(Validation.mixin):
            name: Annotated[str, Validation.Required()]
            email: Annotated[str, Validation.Required()]

        collector.invalidate(M)
        result = Required.collect_markers(M)
        assert set(result.names()) == {"name", "email"}

    def test_markers_method(self):
        class M(Validation.mixin):
            name: Annotated[str, Validation.Required()]

        collector.invalidate(M)
        result = Required.collect_markers(M)
        markers_list = result.values_list()
        assert len(markers_list) == 1
        assert markers_list[0].marker_name == "required"

    def test_where_returns_empty_on_no_match(self):
        result = _SMState.collect_markers(_SMachineNoInitial).where(lambda m: m.initial)
        assert len(result) == 0

    def test_real_world_state_machine_pattern(self):
        """Test the full pattern from the real-world usage example."""
        # Collect states — no None checks needed
        states = _SMState.collect_markers(_SMachineFull)
        state_names = states.names()
        assert set(state_names) == {"idle", "running", "done", "error"}

        # get_one for initial state
        initial_name, _ = states.where(lambda m: m.initial).get_one()
        assert initial_name == "idle"

        # Multiple finals
        finals = states.where(lambda m: m.final)
        assert set(finals.keys()) == {"done", "error"}

        # Transitions — direct marker param access
        transitions = _SMTransition.collect_markers(_SMachineFull)
        assert set(transitions.keys()) == {"start", "finish", "fail"}
        assert transitions["start"].source == ["idle"]
        assert transitions["start"].target == "running"
        assert transitions["finish"].target == "done"
        assert transitions["fail"].target == "error"
