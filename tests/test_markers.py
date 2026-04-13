"""
Tests for markers.

Run with: pytest tests/ -v
"""

from typing import Annotated

import pytest

from markers import MISSING, Marker, MarkerGroup, MemberInfo, MemberKind, Registry
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
