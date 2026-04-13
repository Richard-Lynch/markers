"""
Comprehensive usage example for the markers library.

Demonstrates every public API feature across realistic use cases.
Run with: python examples/example.py
"""

from typing import Annotated

from pydantic import ValidationError

from markers import MISSING, Marker, MarkerGroup, Registry

# ===================================================================
# 1. Define markers
# ===================================================================

print("=" * 60)
print("1. Define Markers")
print("=" * 60)


# Schema-less markers (tags with no parameters)
class Required(Marker):
    pass


class Unique(Marker):
    pass


class Filterable(Marker):
    pass


class Sortable(Marker):
    pass


# Schema markers (with typed, validated parameters)
class MaxLen(Marker):
    mark = "max_length"
    limit: int


class Searchable(Marker):
    boost: float = 1.0
    analyzer: str = "standard"


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


# Intermediate base with shared schema fields
class LifecycleMarker(Marker):
    priority: int = 0


class OnSave(LifecycleMarker):
    mark = "on_save"


class OnDelete(LifecycleMarker):
    mark = "on_delete"


print(f"Required:    {Required}")
print(f"Searchable:  {Searchable}")
print(f"OnSave:      {OnSave}")


# ===================================================================
# 2. Schema validation
# ===================================================================

print("\n" + "=" * 60)
print("2. Schema Validation")
print("=" * 60)

inst = Searchable(boost=2.5)
print(f"inst.boost:    {inst.boost}")
print(f"inst.analyzer: {inst.analyzer}")
print(f"inst.as_dict(): {inst.as_dict()}")

# MarkerInstance equality
print(f"\nEquality: MaxLen(limit=100) == MaxLen(limit=100) -> {MaxLen(limit=100) == MaxLen(limit=100)}")
print(f"Equality: MaxLen(limit=100) == MaxLen(limit=200) -> {MaxLen(limit=100) == MaxLen(limit=200)}")

# MISSING sentinel
print(f"\nMISSING repr: {MISSING!r}")
print(f"MISSING bool: {bool(MISSING)}")

# Validation errors
errors = []
try:
    Required(oops=True)  # type: ignore[call-arg]
except TypeError as e:
    errors.append(f"No params allowed: {e}")
try:
    MaxLen()  # type: ignore[call-arg]
except ValidationError:
    errors.append("Missing required: limit")
try:
    MaxLen(limit="nope")  # type: ignore[arg-type]
except ValidationError:
    errors.append("Wrong type: limit must be int")

print(f"\nValidation errors caught: {len(errors)}")
for err in errors:
    print(f"  {err}")


# ===================================================================
# 3. MarkerGroup — attribute-based and list-based syntax
# ===================================================================

print("\n" + "=" * 60)
print("3. MarkerGroup")
print("=" * 60)


# Attribute-based syntax (with aliasing support)
class DB(MarkerGroup):
    PrimaryKey = PrimaryKey
    Indexed = Indexed
    Unique = Unique
    ForeignKey = ForeignKey


# List-based syntax (no X = X stutter)
class Search(MarkerGroup):
    markers = [Searchable, Filterable, Sortable]


class Validation(MarkerGroup):
    markers = [Required, MaxLen, Pattern]


class Lifecycle(MarkerGroup):
    markers = [OnSave, OnDelete]


print(f"DB markers:         {list(DB._markers.keys())}")
print(f"Search markers:     {list(Search._markers.keys())}")
print(f"Validation markers: {list(Validation._markers.keys())}")
print(f"Lifecycle markers:  {list(Lifecycle._markers.keys())}")


# ===================================================================
# 4. MarkerGroup.combine() — single mixin from multiple groups
# ===================================================================

print("\n" + "=" * 60)
print("4. MarkerGroup.combine()")
print("=" * 60)

# combine() merges all descriptors into one mixin — one type: ignore
# instead of one per group in the inheritance list
AppMixin = MarkerGroup.combine(DB, Search, Validation, Lifecycle)  # type: ignore[assignment]
print(f"Combined mixin: {AppMixin}")
print(f"Has .required descriptor: {hasattr(AppMixin, 'required')}")
print(f"Has .primary_key descriptor: {hasattr(AppMixin, 'primary_key')}")


# ===================================================================
# 5. Models using the combined mixin
# ===================================================================

print("\n" + "=" * 60)
print("5. Models")
print("=" * 60)


class TimestampMixin:
    created_at: Annotated[str, Indexed(), Sortable()]
    updated_at: Annotated[str, Indexed()]


class User(TimestampMixin, AppMixin):  # type: ignore[misc,valid-type]
    id: Annotated[int, PrimaryKey()]
    name: Annotated[str, Required(), MaxLen(limit=100), Searchable(boost=2.0)]
    email: Annotated[str, Required(), Pattern(regex=r".+@.+"), Indexed(unique=True)]
    bio: Annotated[str, Searchable()] = ""

    @OnSave(priority=10)
    def validate_required(self) -> list[str]:
        errs = []
        for field_name, info in type(self).required.items():
            if info.is_field and not getattr(self, field_name, None):
                errs.append(f"{field_name} is required")
        return errs

    @OnSave(priority=20)
    def validate_lengths(self) -> list[str]:
        errs = []
        # Use Marker class in .get() — no string typo risk
        for field_name, info in type(self).max_length.items():
            if info.is_field:
                val = getattr(self, field_name, "")
                if len(str(val)) > info.get(MaxLen).limit:
                    errs.append(f"{field_name} too long")
        return errs

    @OnDelete()
    def check_deletable(self) -> list[str]:
        return []


print(f"User.fields:      {list(User.fields.keys())}")
print(f"User.methods:     {list(User.methods.keys())}")
print(f"User.required:    {list(User.required.keys())}")
print(f"User.searchable:  {list(User.searchable.keys())}")


# ===================================================================
# 6. MemberInfo — querying with Marker classes (not just strings)
# ===================================================================

print("\n" + "=" * 60)
print("6. MemberInfo Querying")
print("=" * 60)

name_info = User.fields["name"]
print(f"name has Required: {name_info.has(Required)}")
print(f"name has Indexed:  {name_info.has(Indexed)}")
print(f"name MaxLen.limit: {name_info.get(MaxLen).limit}")
print(f"name Searchable:   {name_info.get(Searchable).boost}")

# get_marker() raises instead of returning None
email_info = User.fields["email"]
print(f"email pattern:     {email_info.get_marker(Pattern).regex}")


# ===================================================================
# 7. collect_markers() — direct marker access, no None checks
# ===================================================================

print("\n" + "=" * 60)
print("7. collect_markers()")
print("=" * 60)

# Returns CollectResult mapping names to MarkerInstance directly
results = Searchable.collect_markers(User)
print(f"Searchable fields: {results.names()}")
for field_name, marker in results.items():
    print(f"  {field_name}: boost={marker.boost}, analyzer={marker.analyzer}")

# .where() + .get_one_name() for uniqueness assertions
pk_name = PrimaryKey.collect_markers(User).get_one_name("primary key")
print(f"\nPrimary key: {pk_name}")


# ===================================================================
# 8. collect() — returns CollectResult[MemberInfo] with same API
# ===================================================================

print("\n" + "=" * 60)
print("8. collect() with CollectResult")
print("=" * 60)

# collect() now returns CollectResult[MemberInfo] — same .where(), .get_one() etc.
required_fields = Required.collect(User)
print(f"Required fields: {required_fields.names()}")

# .where() on MemberInfo — filter by type, default, kind, etc.
required_no_default = required_fields.where(lambda info: not info.has_default)
print(f"Required without default: {required_no_default.names()}")


# ===================================================================
# 9. Lifecycle hooks — sorted_by() for priority ordering
# ===================================================================

print("\n" + "=" * 60)
print("9. Lifecycle Hooks (sorted_by)")
print("=" * 60)

# sorted_by() eliminates manual sorted(..., key=lambda ...) boilerplate
save_hooks = OnSave.collect_markers(User).sorted_by("priority")
for hook_name, hook_marker in save_hooks:
    print(f"  {hook_name}: priority={hook_marker.priority}")

# Execute hooks in priority order
user = User()
user.name = ""
user.email = "test@test.com"

all_errors: list[str] = []
for hook_name, _hook_marker in save_hooks:
    all_errors.extend(getattr(user, hook_name)())
print(f"\nSave errors: {all_errors}")


# ===================================================================
# 10. classmethod / staticmethod support
# ===================================================================

print("\n" + "=" * 60)
print("10. classmethod/staticmethod support")
print("=" * 60)


class Service(Lifecycle.mixin):
    @OnSave(priority=1)
    @classmethod
    def class_hook(cls) -> None:
        pass

    @OnSave(priority=2)
    @staticmethod
    def static_hook() -> None:
        pass


service_hooks = OnSave.collect_markers(Service)
print(f"Service.methods: {list(Service.methods.keys())}")
print(f"class_hook collected: {'class_hook' in service_hooks}")
print(f"static_hook collected: {'static_hook' in service_hooks}")


# ===================================================================
# 11. Registry — cross-class queries
# ===================================================================

print("\n" + "=" * 60)
print("11. Registry")
print("=" * 60)


class Entity(AppMixin, Registry):  # type: ignore[misc,valid-type]
    id: Annotated[int, PrimaryKey()]


class Customer(Entity):
    name: Annotated[str, Required(), MaxLen(limit=100), Searchable()]
    email: Annotated[str, Required(), Indexed(unique=True)]
    tier: Annotated[str, Filterable()] = "free"


class Order(Entity):
    customer_id: Annotated[int, ForeignKey(table="customers", column="id")]
    total: Annotated[float, Required()]
    status: Annotated[str, Required(), Filterable()] = "pending"


class Invoice(Entity):
    order_id: Annotated[int, ForeignKey(table="orders", column="id")]
    amount: Annotated[float, Required()]
    paid: Annotated[bool, Filterable()] = False


print(f"Registered: {[c.__name__ for c in Entity.subclasses()]}")
print(f"AllProxy: {Entity.all!r}")

# .all gathers into dict[str, list[MemberInfo]]
print("\nEntity.all.required:")
for field_name, infos in Entity.all.required.items():
    owners = [i.owner.__name__ for i in infos if i.owner]
    print(f"  {field_name}: defined on {owners}")

print("\nEntity.all.foreign_key:")
for field_name, infos in Entity.all.foreign_key.items():
    for info in infos:
        fk = info.get_marker(ForeignKey)
        owner_name = info.owner.__name__ if info.owner else "?"
        print(f"  {owner_name}.{field_name} -> {fk.table}.{fk.column} ({fk.on_delete})")

# Per-class iteration via subclasses()
print("\nPer-class iteration:")
for cls in Entity.subclasses():
    req = Required.collect_markers(cls)
    print(f"  {cls.__name__}: required={req.names()}")


# ===================================================================
# 12. Cache invalidation + imperative collection
# ===================================================================

print("\n" + "=" * 60)
print("12. Invalidation + Imperative")
print("=" * 60)

before = list(Customer.fields.keys())
Marker.invalidate(Customer)
after = list(Customer.fields.keys())
print(f"Invalidate: before={len(before)} after={len(after)} match={before == after}")

# collect() is the typed imperative API
print(f"Required.collect(Customer):   {list(Required.collect(Customer).keys())}")
print(f"Searchable.collect(Customer): {list(Searchable.collect(Customer).keys())}")
print(f"ForeignKey.collect(Order):    {list(ForeignKey.collect(Order).keys())}")

# Guard: Marker.collect() itself cannot be used (must use subclass)
try:
    Marker.collect(Customer)
except TypeError:
    print("Marker.collect guard: OK")

# Guard: must pass a class, not an instance
try:
    Required.collect("not a class")  # type: ignore[arg-type]
except TypeError:
    print("Instance guard: OK")
