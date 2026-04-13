# markers

[![CI](https://github.com/Richard-Lynch/markers/actions/workflows/ci.yml/badge.svg)](https://github.com/Richard-Lynch/markers/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/code-is-magic-markers)](https://pypi.org/project/code-is-magic-markers/)
[![Python](https://img.shields.io/pypi/pyversions/code-is-magic-markers)](https://pypi.org/project/code-is-magic-markers/)
[![License](https://img.shields.io/github/license/Richard-Lynch/markers)](https://github.com/Richard-Lynch/markers/blob/main/LICENSE)

Lightweight class introspection toolkit for Python. Define typed markers, annotate fields and methods, collect metadata via MRO-walking descriptors.

## Install

```bash
pip install code-is-magic-markers
```

## Quick start

```python
from typing import Annotated
from markers import Marker, MarkerGroup, Registry

# 1. Define markers — the class body IS the schema
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

# Introspect
User.fields["name"].get("max_length").limit  # 100
User.methods["validate"].get("on_save").priority  # 10
```

## Core concepts

### Marker

Subclass `Marker` to define a marker. The class body is the pydantic schema — typed fields become validated parameters:

```python
class ForeignKey(Marker):
    mark = "foreign_key"  # explicit name (default: lowercased class name)
    table: str            # required parameter
    column: str = "id"    # optional with default
    on_delete: str = "CASCADE"
```

Markers work as both `Annotated[]` metadata and method decorators:

```python
# As annotation
author_id: Annotated[int, ForeignKey(table="users")]

# As decorator
@OnSave(priority=10)
def validate(self): ...
```

Schema-less markers accept no parameters:

```python
class Required(Marker): pass
Required()        # ok
Required(x=1)     # TypeError
```

Intermediate bases share schema fields:

```python
class LifecycleMarker(Marker):
    priority: int = 0

class OnSave(LifecycleMarker):
    mark = "on_save"

class OnDelete(LifecycleMarker):
    mark = "on_delete"

# Both have 'priority'
```

### MarkerGroup

Bundle related markers and produce a `.mixin`:

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
User.fields       # all fields (from BaseMixin)
```

Groups compose via inheritance:

```python
class ExtendedDB(DB):
    Unique = Unique
```

### Registry

Track subclasses for cross-class queries:

```python
class Entity(DB.mixin, Registry):
    id: Annotated[int, DB.PrimaryKey()]

class User(Entity):
    name: Annotated[str, Required()]

class Post(Entity):
    title: Annotated[str, Required()]

# List all subclasses
Entity.subclasses()  # [User, Post]

# Iterate with the same per-class API
for cls in Entity.subclasses():
    print(cls.__name__, list(cls.required.keys()))

# Or gather across all subclasses
Entity.all.required  # {'name': [MemberInfo(owner=User)], 'title': [MemberInfo(owner=Post)]}
Entity.all.fields    # {'id': [MemberInfo(owner=User), MemberInfo(owner=Post)], ...}
```

### MemberInfo

Every collected member (field or method) is a `MemberInfo`:

```python
info = User.fields["name"]
info.name          # 'name'
info.kind          # MemberKind.FIELD
info.type          # <class 'str'>
info.owner         # <class 'User'>
info.default       # MISSING (no default)
info.has_default   # False
info.is_field      # True
info.is_method     # False
info.markers       # [MarkerInstance('required', ...), MarkerInstance('max_length', ...)]
info.has("required")              # True
info.get("max_length").limit      # 100
info.get_all("required")          # [MarkerInstance(...)]
```

## API reference

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

## License

MIT
