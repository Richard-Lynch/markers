"""
Full usage example for markers.

Public API: Marker, MarkerGroup, Registry.
"""

from typing import Annotated

from pydantic import ValidationError

from markers import Marker, MarkerGroup, Registry

# ===================================================================
# 1. Define markers
# ===================================================================

print("=" * 60)
print("1. Define Markers")
print("=" * 60)


# Schema-less
class Required(Marker):
    pass


class Unique(Marker):
    pass


class Filterable(Marker):
    pass


class Sortable(Marker):
    pass


class Facetable(Marker):
    pass


# With schema
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


class Pattern(Marker):
    regex: str


# Intermediate base with shared schema
class LifecycleMarker(Marker):
    priority: int = 0


class OnSave(LifecycleMarker):
    mark = "on_save"


class OnDelete(LifecycleMarker):
    mark = "on_delete"


print(f"Required:        {Required}")
print(f"Searchable:      {Searchable}")
print(f"LifecycleMarker: {LifecycleMarker}")
print(f"OnSave:          {OnSave}")
print(f"OnDelete:        {OnDelete}")


# ===================================================================
# 2. Schema validation
# ===================================================================

print("\n" + "=" * 60)
print("2. Schema Validation")
print("=" * 60)

print(f"Required():          {Required()}")
print(f"MaxLen(limit=100):   {MaxLen(limit=100)}")
print(f"Searchable():        {Searchable()}")
print(f"OnSave():            {OnSave()}")
print(f"OnSave(priority=10): {OnSave(priority=10)}")

inst = Searchable(boost=2.5)
print(f"\ninst.boost:    {inst.boost}")
print(f"inst.analyzer: {inst.analyzer}")

save_inst = OnSave(priority=5)
print(f"save.priority: {save_inst.priority}")

errors = []
try:
    Required(oops=True)  # type: ignore[call-arg]
except TypeError as e:
    errors.append(f"No params: {e}")
try:
    MaxLen()  # type: ignore[call-arg]
except ValidationError as e:
    errors.append(f"Missing: {e}")
try:
    MaxLen(limit="nope")  # type: ignore[arg-type]
except ValidationError as e:
    errors.append(f"Type: {e}")

print("\nValidation errors:")
for err in errors:
    print(f"  {err}")


# ===================================================================
# 3. MarkerGroup
# ===================================================================

print("\n" + "=" * 60)
print("3. MarkerGroup")
print("=" * 60)


class DB(MarkerGroup):
    PrimaryKey = PrimaryKey
    Indexed = Indexed
    Unique = Unique
    ForeignKey = ForeignKey


class Search(MarkerGroup):
    Searchable = Searchable
    Filterable = Filterable
    Sortable = Sortable
    Facetable = Facetable


class Validation(MarkerGroup):
    Required = Required
    MaxLen = MaxLen
    Pattern = Pattern
    Range = Range


class Lifecycle(MarkerGroup):
    OnSave = OnSave
    OnDelete = OnDelete


print(f"DB markers:         {list(DB._markers.keys())}")
print(f"Search markers:     {list(Search._markers.keys())}")
print(f"Validation markers: {list(Validation._markers.keys())}")
print(f"Lifecycle markers:  {list(Lifecycle._markers.keys())}")


# ===================================================================
# 4. Models with MarkerGroup mixins
# ===================================================================

print("\n" + "=" * 60)
print("4. Models")
print("=" * 60)


class TimestampMixin:
    created_at: Annotated[str, DB.Indexed(), Search.Sortable()]
    updated_at: Annotated[str, DB.Indexed()]


class SoftDeleteMixin:
    deleted_at: Annotated[str | None, DB.Indexed()] = None
    is_deleted: Annotated[bool, Search.Filterable()] = False


class User(  # type: ignore[misc]  # multiple group mixins resolve at runtime
    TimestampMixin,
    SoftDeleteMixin,
    DB.mixin,
    Search.mixin,
    Validation.mixin,
    Lifecycle.mixin,
):
    id: Annotated[int, DB.PrimaryKey()]
    name: Annotated[str, Validation.Required(), Validation.MaxLen(limit=100), Search.Searchable(boost=2.0)]
    email: Annotated[str, Validation.Required(), Validation.Pattern(regex=r".+@.+"), DB.Indexed(unique=True)]
    bio: Annotated[str, Search.Searchable()] = ""
    age: Annotated[int, Validation.Range(min=0, max=150)] = 0

    @Lifecycle.OnSave(priority=10)
    def validate_required(self) -> list[str]:
        errors = []
        for name, info in type(self).required.items():
            if info.is_field and not getattr(self, name, None):
                errors.append(f"{name} is required")
        return errors

    @Lifecycle.OnSave(priority=20)
    def validate_lengths(self) -> list[str]:
        errors = []
        for name, info in type(self).max_length.items():
            if info.is_field:
                val = getattr(self, name, "")
                if len(str(val)) > info.get("max_length").limit:
                    errors.append(f"{name} too long")
        return errors

    @Lifecycle.OnDelete()
    def check_deletable(self) -> list[str]:
        return []


print(f"User.fields:      {list(User.fields.keys())}")
print(f"User.methods:     {list(User.methods.keys())}")
print(f"User.required:    {list(User.required.keys())}")
print(f"User.searchable:  {list(User.searchable.keys())}")
print(f"User.on_save:     {list(User.on_save.keys())}")

print(f"\nname boost:     {User.fields['name'].get('searchable').boost}")
print(f"email unique:   {User.fields['email'].get('indexed').unique}")
print(f"id auto_inc:    {User.fields['id'].get('primary_key').auto_increment}")


# ===================================================================
# 5. Lifecycle with priority
# ===================================================================

print("\n" + "=" * 60)
print("5. Lifecycle")
print("=" * 60)

save_hooks = sorted(
    [(n, i) for n, i in User.on_save.items() if i.is_method],
    key=lambda x: x[1].get("on_save").priority,
)
for name, info in save_hooks:
    print(f"  {name}: priority={info.get('on_save').priority}")

user = User()
user.name = ""
user.email = "test@test.com"

errs = []
for name, _info in save_hooks:
    errs.extend(getattr(user, name)())
print(f"\nSave errors: {errs}")

user.name = "Alice"
errs = []
for name, _info in save_hooks:
    errs.extend(getattr(user, name)())
print(f"Save fixed:  {errs}")


# ===================================================================
# 6. Registry
# ===================================================================

print("\n" + "=" * 60)
print("6. Registry")
print("=" * 60)


class Entity(  # type: ignore[misc]  # multiple group mixins resolve at runtime
    TimestampMixin,
    SoftDeleteMixin,
    DB.mixin,
    Search.mixin,
    Validation.mixin,
    Lifecycle.mixin,
    Registry,
):
    id: Annotated[int, DB.PrimaryKey()]


class Customer(Entity):
    name: Annotated[str, Validation.Required(), Validation.MaxLen(limit=100), Search.Searchable()]
    email: Annotated[str, Validation.Required(), DB.Indexed(unique=True)]
    tier: Annotated[str, Search.Facetable()] = "free"


class Order(Entity):
    customer_id: Annotated[int, DB.ForeignKey(table="customers", column="id")]
    total: Annotated[float, Validation.Required(), Validation.Range(min=0, max=999999)]
    status: Annotated[str, Validation.Required(), Search.Facetable()] = "pending"


class Invoice(Entity):
    order_id: Annotated[int, DB.ForeignKey(table="orders", column="id")]
    amount: Annotated[float, Validation.Required()]
    paid: Annotated[bool, Search.Filterable()] = False


print(f"Registered: {[c.__name__ for c in Entity.subclasses()]}")

# --- .all gathers into dict[str, list[MemberInfo]] ---
print("\nEntity.all.fields:")
for name, infos in Entity.all.fields.items():
    owners = [i.owner.__name__ for i in infos]
    print(f"  {name}: {owners}")

print("\nEntity.all.methods:")
for name, infos in Entity.all.methods.items():
    owners = [i.owner.__name__ for i in infos]
    print(f"  {name}: {owners}")

print("\nEntity.all.required:")
for name, infos in Entity.all.required.items():
    owners = [i.owner.__name__ for i in infos]
    print(f"  {name}: defined on {owners}")

print("\nEntity.all.foreign_key:")
for name, infos in Entity.all.foreign_key.items():
    for info in infos:
        fk = info.get("foreign_key")
        print(f"  {info.owner.__name__}.{name} -> {fk.table}.{fk.column} ({fk.on_delete})")

print("\nEntity.all.searchable:")
for name, infos in Entity.all.searchable.items():
    for info in infos:
        print(f"  {info.owner.__name__}.{name}: boost={info.get('searchable').boost}")

# --- subclasses() for per-class iteration ---
print("\nPer-class iteration:")
for cls in Entity.subclasses():
    print(f"  {cls.__name__}.required: {list(cls.required.keys())}")

# Registry itself has fields/methods via BaseMixin
print(f"\nEntity.fields: {list(Entity.fields.keys())}")


# ===================================================================
# 7. Cache invalidation + imperative collection
# ===================================================================

print("\n" + "=" * 60)
print("7. Invalidation + Imperative")
print("=" * 60)

before = list(Customer.fields.keys())
Marker.invalidate(Customer)
after = list(Customer.fields.keys())
print(f"Invalidate: before={len(before)} after={len(after)} match={before == after}")

print(f"Required.collect(Customer):   {list(Required.collect(Customer).keys())}")
print(f"Searchable.collect(Customer): {list(Searchable.collect(Customer).keys())}")
print(f"ForeignKey.collect(Order):    {list(ForeignKey.collect(Order).keys())}")

try:
    Marker.collect(Customer)
except TypeError as e:
    print(f"Marker.collect guard: {e}")
