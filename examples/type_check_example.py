"""
Example for validating type checker behavior with markers.

Open this file in your IDE (Pylance/Pyright) and verify:
- .fields, .members, .methods are fully typed as dict[str, MemberInfo]
- .items(), .keys(), .values() all work on descriptor results
- Decorated methods preserve their signatures
- Registry .all proxy returns dict[str, list[MemberInfo]]

Marker-specific descriptors (.primary_key, .required, etc.) are
dynamic — type checkers can't see them without help. Two options:

1. Use Marker.collect(cls) — fully typed, no annotations needed.
2. Add ClassVar annotations under TYPE_CHECKING on your class.
"""

from typing import TYPE_CHECKING, Annotated, ClassVar

from markers import Marker, MarkerGroup, MemberInfo, Registry

# -- Markers --


class Required(Marker):
    pass


class MaxLen(Marker):
    mark = "max_length"
    limit: int


class PrimaryKey(Marker):
    mark = "primary_key"
    auto_increment: bool = True


class Indexed(Marker):
    unique: bool = False


class Transition(Marker):
    source: list[str]
    target: str


# -- Groups --


class Validation(MarkerGroup):
    Required = Required
    MaxLen = MaxLen


class DB(MarkerGroup):
    PrimaryKey = PrimaryKey
    Indexed = Indexed


class SM(MarkerGroup):
    Transition = Transition


# ============================================================
# 1. BaseMixin descriptors: always typed
# ============================================================


class User(DB.mixin):
    id: Annotated[int, DB.PrimaryKey()]
    email: Annotated[str, DB.Indexed(unique=True)]


# .fields, .methods, .members — all dict[str, MemberInfo]
fields: dict[str, MemberInfo] = User.fields
methods: dict[str, MemberInfo] = User.methods
members: dict[str, MemberInfo] = User.members

# .items() yields (str, MemberInfo)
for field_name, info in User.fields.items():
    print(f"{field_name}: is_field={info.is_field}, has_default={info.has_default}")

for field_name in User.fields:
    print(field_name)

for info in User.fields.values():
    print(info.name, info.kind)


# ============================================================
# 2. MemberInfo methods
# ============================================================

id_info = User.fields["id"]
print(id_info.has("primary_key"))  # bool
print(id_info.get("primary_key"))  # MarkerInstance | None
print(id_info.get_all("primary_key"))  # list[MarkerInstance]


# ============================================================
# 3. Marker-specific descriptors: option A — Marker.collect()
#    Fully typed, no annotations needed.
# ============================================================

pk: dict[str, MemberInfo] = PrimaryKey.collect(User)
idx: dict[str, MemberInfo] = Indexed.collect(User)

for field_name, info in PrimaryKey.collect(User).items():
    marker = info.get("primary_key")
    print(f"{field_name}: has pk = {marker is not None}")


# ============================================================
# 4. Marker-specific descriptors: option B — ClassVar annotations
#    Opt-in explicit typing for descriptor access on the class.
# ============================================================


class Product(DB.mixin):
    if TYPE_CHECKING:
        primary_key: ClassVar[dict[str, MemberInfo]]
        indexed: ClassVar[dict[str, MemberInfo]]

    id: Annotated[int, DB.PrimaryKey()]
    sku: Annotated[str, DB.Indexed(unique=True)]


# Now type checkers know about these:
product_pk: dict[str, MemberInfo] = Product.primary_key
product_idx: dict[str, MemberInfo] = Product.indexed

for field_name, info in Product.primary_key.items():
    print(f"{field_name}: {info.name}")


# ============================================================
# 5. Decorator preserves function type
# ============================================================


class Task(SM.mixin):
    title: Annotated[str, SM.Transition(source=["backlog"], target="todo")]

    @SM.Transition(source=["backlog"], target="todo")
    def move_to_todo(self) -> str:
        return "moved"

    @SM.Transition(source=["todo", "in_progress"], target="done")
    def complete(self) -> bool:
        return True


task = Task()

# These preserve the original return types
result_str: str = task.move_to_todo()
result_bool: bool = task.complete()


# ============================================================
# 6. Registry .all proxy: dict[str, list[MemberInfo]]
# ============================================================


class Entity(DB.mixin, Registry):
    id: Annotated[int, DB.PrimaryKey()]


class Customer(Entity):
    tier: Annotated[str, DB.Indexed()] = "free"


class Order(Entity):
    total: Annotated[float, DB.Indexed(unique=True)]


all_fields: dict[str, list[MemberInfo]] = Entity.all.fields

for member_name, infos in Entity.all.fields.items():
    owners = [i.owner.__name__ for i in infos if i.owner]
    print(f"{member_name}: {owners}")

for cls in Entity.subclasses():
    print(cls.__name__)
