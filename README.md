# markers

[![CI](https://github.com/Richard-Lynch/markers/actions/workflows/ci.yml/badge.svg)](https://github.com/Richard-Lynch/markers/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/code-is-magic-markers)](https://pypi.org/project/code-is-magic-markers/)
[![Python](https://img.shields.io/pypi/pyversions/code-is-magic-markers)](https://pypi.org/project/code-is-magic-markers/)
[![License](https://img.shields.io/github/license/Richard-Lynch/markers)](https://github.com/Richard-Lynch/markers/blob/main/LICENSE)

Lightweight class introspection toolkit for Python. Define typed markers, annotate fields and methods, collect metadata via MRO-walking descriptors.

## Why markers?

Python's `Annotated` type lets you attach metadata to fields, but there's no standard way to:

- **Define** what that metadata looks like (with validation)
- **Collect** it from a class and its entire MRO
- **Query** it with a consistent API across fields and methods
- **Aggregate** it across a family of related classes

`markers` solves all four. You define markers as classes (with optional pydantic schemas), attach them via `Annotated` or as decorators, and query everything through descriptors that walk the MRO and cache results automatically.

```python
# Without markers — manual, fragile, no validation
class User:
    name: Annotated[str, {"required": True, "max_length": 100}]  # just a dict, no validation
    email: Annotated[str, {"required": True}]

# With markers — typed, validated, queryable
class User(Validation.mixin):
    name: Annotated[str, Validation.Required(), Validation.MaxLen(limit=100)]
    email: Annotated[str, Validation.Required()]

User.required        # {'name': MemberInfo(...), 'email': MemberInfo(...)}
User.fields["name"].get("max_length").limit  # 100 — typed, validated access
```

## Install

```bash
pip install code-is-magic-markers
```

Requires Python 3.10+ and pydantic 2.0+.

## Quick start

```python
from typing import Annotated
from markers import Marker, MarkerGroup, Registry

# 1. Define markers — the class body IS the pydantic schema
class Required(Marker): pass

class MaxLen(Marker):
    mark = "max_length"
    limit: int

class Searchable(Marker):
    boost: float = 1.0
    analyzer: str = "standard"

class OnSave(Marker):
    mark = "on_save"
    priority: int = 0


# 2. Bundle into groups
class Validation(MarkerGroup):
    Required = Required
    MaxLen = MaxLen

class Lifecycle(MarkerGroup):
    OnSave = OnSave


# 3. Annotate your classes
class User(Validation.mixin, Lifecycle.mixin):
    name: Annotated[str, Validation.Required(), Validation.MaxLen(limit=100)]
    email: Annotated[str, Validation.Required()]
    bio: Annotated[str, Searchable()] = ""

    @Lifecycle.OnSave(priority=10)
    def validate(self) -> list[str]:
        errors = []
        for name, info in type(self).required.items():
            if info.is_field and not getattr(self, name, None):
                errors.append(f"{name} is required")
        return errors


# 4. Query metadata — same dict[str, MemberInfo] everywhere
User.fields          # all fields
User.methods         # all methods
User.members         # both
User.required        # only members marked 'required'
User.on_save         # only members marked 'on_save'

# Introspect individual members
User.fields["name"].get("max_length").limit  # 100
User.methods["validate"].get("on_save").priority  # 10
```

## Core concepts

### Marker

Subclass `Marker` to define a marker. The class body is the pydantic schema — typed fields become validated parameters.

```python
class ForeignKey(Marker):
    mark = "foreign_key"  # explicit name (default: lowercased class name)
    table: str            # required parameter
    column: str = "id"    # optional with default
    on_delete: str = "CASCADE"
```

**Calling a marker** creates a `MarkerInstance` with validated parameters:

```python
ForeignKey(table="users")                    # ok
ForeignKey(table="users", column="user_id")  # ok — override default
ForeignKey()                                 # ValidationError — 'table' is required
ForeignKey(table="users", extra=True)        # ValidationError — unknown field
```

**Schema-less markers** accept no parameters:

```python
class Required(Marker): pass

Required()        # ok — empty MarkerInstance
Required(x=1)     # TypeError — no parameters accepted
```

**Using markers** — they work as both `Annotated[]` metadata and method decorators:

```python
# As field annotation
author_id: Annotated[int, ForeignKey(table="users")]

# As method decorator
@OnSave(priority=10)
def validate(self): ...
```

Multiple decorators stack naturally:

```python
@OnSave(priority=10)
@Audited()
def save(self): ...
```

**Marker names** default to the lowercased class name. Set `mark` to override:

```python
class PK(Marker):
    mark = "primary_key"  # queried as .primary_key, not .pk
    auto_increment: bool = True
```

**Intermediate bases** share schema fields across related markers:

```python
class LifecycleMarker(Marker):
    priority: int = 0

class OnSave(LifecycleMarker):
    mark = "on_save"

class OnDelete(LifecycleMarker):
    mark = "on_delete"

# Both have 'priority' with default 0
OnSave()              # priority=0
OnSave(priority=10)   # priority=10
OnDelete(priority=5)  # priority=5
```

### MarkerGroup

Bundle related markers and produce a `.mixin` for your model classes. This is how marker descriptors get onto classes.

```python
class DB(MarkerGroup):
    PrimaryKey = PrimaryKey
    Indexed = Indexed
    ForeignKey = ForeignKey

class User(DB.mixin):
    id: Annotated[int, DB.PrimaryKey()]
    email: Annotated[str, DB.Indexed(unique=True)]

User.primary_key  # {'id': MemberInfo(...)}
User.indexed      # {'email': MemberInfo(...)}
User.fields       # all fields (always available via BaseMixin)
```

The `.mixin` automatically provides:
- A **marker descriptor** for each marker (e.g. `.primary_key`, `.indexed`) — returns `dict[str, MemberInfo]` of members carrying that marker
- **`.fields`**, **`.methods`**, **`.members`** from `BaseMixin` — always available

**Composing groups** — groups inherit from other groups:

```python
class FullDB(DB):
    Unique = Unique
    Check = Check
# FullDB.mixin has all of DB's descriptors plus 'unique' and 'check'
```

**Multiple group mixins** on one class:

```python
class User(DB.mixin, Validation.mixin, Search.mixin, Lifecycle.mixin):
    id: Annotated[int, DB.PrimaryKey()]
    name: Annotated[str, Validation.Required(), Search.Searchable(boost=2.0)]
    email: Annotated[str, Validation.Required(), DB.Indexed(unique=True)]

    @Lifecycle.OnSave(priority=10)
    def validate(self): ...

# All descriptors available
User.primary_key    # from DB
User.required       # from Validation
User.searchable     # from Search
User.on_save        # from Lifecycle
User.fields         # all fields (always)
User.methods        # all methods (always)
```

### Reusable mixins

Factor out common field patterns into plain mixins and compose them:

```python
class TimestampMixin:
    created_at: Annotated[str, DB.Indexed()]
    updated_at: Annotated[str, DB.Indexed()]

class SoftDeleteMixin:
    deleted_at: Annotated[str | None, DB.Indexed()] = None
    is_deleted: Annotated[bool, Search.Filterable()] = False

class User(TimestampMixin, SoftDeleteMixin, DB.mixin, Search.mixin):
    id: Annotated[int, DB.PrimaryKey()]
    name: str

# Fields from all mixins are collected via MRO
User.fields  # id, name, created_at, updated_at, deleted_at, is_deleted
User.indexed  # created_at, updated_at, deleted_at
```

### Registry

Track subclasses and query metadata across all of them:

```python
class Entity(DB.mixin, Validation.mixin, Registry):
    id: Annotated[int, DB.PrimaryKey()]

class User(Entity):
    name: Annotated[str, Validation.Required()]

class Post(Entity):
    title: Annotated[str, Validation.Required()]
```

**List subclasses:**

```python
Entity.subclasses()  # [User, Post]
```

**Per-class access** works the same as always:

```python
User.required  # {'name': MemberInfo(...)}
Post.required  # {'title': MemberInfo(...)}
```

**Cross-class access** via `.all` gathers into `dict[str, list[MemberInfo]]`:

```python
Entity.all.required
# {'name': [MemberInfo(owner=User)], 'title': [MemberInfo(owner=Post)]}

Entity.all.fields
# {'id': [MemberInfo(owner=User), MemberInfo(owner=Post)],
#  'name': [MemberInfo(owner=User)],
#  'title': [MemberInfo(owner=Post)]}
```

Each `MemberInfo` in the list has `.owner` so you know which class it came from.

**Iterate subclasses** with the same per-class API:

```python
for cls in Entity.subclasses():
    print(cls.__name__, list(cls.required.keys()))
# User ['name']
# Post ['title']
```

### MemberInfo

Every collected member (field or method) is a `MemberInfo` with a consistent API:

```python
info = User.fields["name"]
```

| Attribute / Method | Type | Description |
|---|---|---|
| `info.name` | `str` | Member name |
| `info.kind` | `MemberKind` | `MemberKind.FIELD` or `MemberKind.METHOD` |
| `info.type` | `type \| None` | The base type (unwrapped from `Annotated`). `None` for methods. |
| `info.owner` | `type \| None` | The class that defined this member |
| `info.default` | `Any` | Default value, or `MISSING` if none |
| `info.has_default` | `bool` | `True` if a default value exists |
| `info.is_field` | `bool` | `True` if `kind == FIELD` |
| `info.is_method` | `bool` | `True` if `kind == METHOD` |
| `info.markers` | `list[MarkerInstance]` | All markers attached to this member |
| `info.has(name)` | `bool` | Check if a marker is present |
| `info.get(name)` | `MarkerInstance \| None` | Get first matching marker |
| `info.get_all(name)` | `list[MarkerInstance]` | Get all matching markers |

### MarkerInstance

A `MarkerInstance` is what you get when you call a marker. Schema fields are accessible as attributes:

```python
inst = Searchable(boost=2.5, analyzer="english")
inst.marker_name  # 'searchable'
inst.boost        # 2.5
inst.analyzer     # 'english'
```

| Attribute | Type | Description |
|---|---|---|
| `inst.marker_name` | `str` | The marker type name |
| `inst.<field>` | `Any` | Access any schema field as an attribute |

## How collection works

When you access a descriptor like `User.fields` or `User.required`, the library:

1. **Walks the class MRO** in reverse (base classes first, subclass last — so subclasses override)
2. **Collects fields** from `__annotations__` + `get_type_hints(include_extras=True)`, extracting `MarkerInstance` objects from `Annotated` metadata
3. **Collects methods** by finding callables with a `_markers` attribute (set by the decorator)
4. **Caches the result** per-class using weak references — the cache auto-clears when a class is garbage collected

**Private fields** (names starting with `_`) are skipped.

**Subclass overrides** work naturally — if a child redefines a field, the child's version wins:

```python
class Parent(Validation.mixin):
    name: Annotated[str, Validation.Required()]

class Child(Parent):
    name: Annotated[str, Validation.Required(), Validation.MaxLen(limit=50)]

Child.fields["name"].owner  # Child
Child.fields["name"].has("max_length")  # True
```

## Caching and invalidation

Collection results are cached per-class for performance. The cache is:

- **Automatic** — first access triggers collection, subsequent accesses return cached results
- **Weakref-based** — if a class is garbage collected, its cache entry is cleaned up automatically
- **Invalidatable** — call `Marker.invalidate(cls)` to clear the cache for a specific class

```python
# First access collects and caches
User.fields  # walks MRO, caches result
User.fields  # returns cached result (same dict object)

# Invalidate if you've dynamically modified a class
Marker.invalidate(User)
User.fields  # re-collects from scratch
```

You typically don't need to call `invalidate()` — classes are usually defined once at import time. It's useful if you're dynamically modifying classes in tests or metaprogramming.

## Imperative collection

Besides descriptors, you can collect members carrying a specific marker imperatively:

```python
# Via the marker class
Required.collect(User)    # {'name': MemberInfo(...), 'email': MemberInfo(...)}
ForeignKey.collect(Post)  # {'author_id': MemberInfo(...)}

# Invalidation works on any Marker subclass (or Marker itself)
Marker.invalidate(User)
Required.invalidate(User)  # same effect — clears the whole cache for User
```

## API reference

### Classes

| Class | Purpose |
|-------|---------|
| `Marker` | Subclass to define markers with optional typed schema |
| `MarkerGroup` | Subclass to bundle markers into a `.mixin` |
| `Registry` | Subclass to track all subclasses, provides `.subclasses()` and `.all` |
| `MarkerInstance` | A specific usage of a marker with validated params |
| `MemberInfo` | Metadata about a field or method |
| `MemberKind` | Enum: `FIELD` or `METHOD` |
| `MISSING` | Sentinel for fields with no default |

### Marker class methods

| Method | Description |
|--------|-------------|
| `MyMarker.collect(cls)` | Collect members carrying this marker from `cls` |
| `Marker.invalidate(cls)` | Clear cached collection for `cls` |

### Descriptors (available on any class using a group mixin)

| Descriptor | Returns | Description |
|---|---|---|
| `.fields` | `dict[str, MemberInfo]` | All field members |
| `.methods` | `dict[str, MemberInfo]` | All method members |
| `.members` | `dict[str, MemberInfo]` | All members (fields + methods) |
| `.<marker_name>` | `dict[str, MemberInfo]` | Members carrying that specific marker |

### Registry extras

| Attribute / Method | Returns | Description |
|---|---|---|
| `.subclasses()` | `list[type]` | All registered subclasses |
| `.all.fields` | `dict[str, list[MemberInfo]]` | Fields from all subclasses, grouped by name |
| `.all.methods` | `dict[str, list[MemberInfo]]` | Methods from all subclasses, grouped by name |
| `.all.members` | `dict[str, list[MemberInfo]]` | All members from all subclasses |
| `.all.<marker_name>` | `dict[str, list[MemberInfo]]` | Marker-filtered, from all subclasses |

## License

MIT
