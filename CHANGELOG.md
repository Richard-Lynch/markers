# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-04-13

### Added

- `Marker.collect_markers()` — returns `CollectResult` mapping names to `MarkerInstance` directly, eliminating `.get()` + None-check boilerplate
- `CollectResult` — generic dict subclass with `.where()`, `.get_one()`, `.get_first()`, `.sorted_by()`, `.get_one_name()`, `.get_first_name()`, `.names()`, `.values_list()`
- `MemberInfo.get_marker()` — like `.get()` but raises `KeyError` instead of returning `None`
- `MemberInfo.has()` / `.get()` / `.get_marker()` / `.get_all()` now accept `Marker` classes alongside strings — `info.has(Required)` catches typos at import time
- `MarkerGroup.combine(*groups)` — creates a single mixin from multiple groups, eliminating `# type: ignore[misc]` for multi-group inheritance
- `MarkerInstance.__eq__` — structural equality comparing marker name and parameters
- `MarkerInstance.as_dict()` — public parameter introspection (replaces private `_params.model_dump()`)
- List-based group definition syntax — `markers = [Required, MaxLen]` as alternative to `Required = Required`
- `CollectResult` is generic — `CollectResult[Self]` in stubs gives typed marker param access
- `registry.pyi` stub — fixes MRO/metaclass conflicts when combining group mixins with `Registry`

### Changed

- `Marker.collect()` now returns `CollectResult[MemberInfo]` (was plain `dict`) — same `.where()`, `.get_one()` etc. methods
- `MISSING` sentinel is now a proper singleton class with `__repr__` returning `"MISSING"` and `__bool__` returning `False`
- `AllProxy` has a useful `__repr__` showing registry name and subclass count
- `groups.pyi` uses `TypeAlias` for `mixin` so mypy accepts `DB.mixin` as a base class (was 29 mypy errors)
- Examples consolidated into a single comprehensive file showcasing all features
- Makefile: fixed broken `deps` target, help regex shows colon targets, lint/typecheck include examples/

### Fixed

- `classmethod`/`staticmethod`/`property` markers were silently lost during collection — now both the decorator and collector unwrap descriptors
- Registry abstract intermediate classes incorrectly captured leaf registrations — leaves now register with nearest non-abstract ancestor
- Multiple registry inheritance only registered with the first base — now registers with all registry roots
- `collect()` / `collect_markers()` now reject instances with a clear error message (was confusing traceback)
- `get_one()` error message truncates key list for large results (was unreadable with 50+ entries)

## [0.3.0] - 2026-04-13

### Added

- PEP 681 `dataclass_transform` support — marker constructor parameters (`MaxLen(limit=100)`) are fully validated by type checkers (Pylance, Pyright, mypy). Typos, wrong types, and missing required params are caught statically.
- Type stubs (`marker.pyi`, `groups.pyi`) for full IDE integration
- `BaseMixinMeta` metaclass for generated mixin classes
- `.fields`, `.methods`, `.members` are now fully typed as `dict[str, MemberInfo]` on any class using a group mixin
- Decorator usage (`@OnSave(priority=10)`) preserves the decorated function's type signature
- Type checking example (`examples/type_check_example.py`) demonstrating all typed patterns
- "Type checking" section in README documenting what's typed and escape hatches for dynamic descriptors

### Changed

- `MarkerInstance.__call__` signature uses `TypeVar` to preserve decorated function types
- `MarkerGroupMeta.__new__` return type narrowed to `MarkerGroupMeta` (was `type`)
- `MarkerGroup.mixin` typed as `type[BaseMixin]` (was `type`)
- Generated mixin classes now use `BaseMixinMeta` metaclass (was `type`)
- Removed `from __future__ import annotations` from `groups.py` for better type checker resolution

## [0.2.0] - 2026-04-13

### Added

- Python 3.14 support (PEP 749 deferred annotations)
- Python 3.14 in CI test matrix, tox env list, and pyproject.toml classifiers

### Changed

- `MarkerMeta.__new__` restructured to read annotations from the created class rather than the namespace dict, for compatibility with Python 3.14.4+ where `__annotations__` is no longer populated in the namespace
- `Collector.collect` uses `annotationlib.get_annotations(format=STRING)` on Python 3.14+ instead of reading `__annotations__` directly
- CI lint, typecheck, and coverage jobs now default to Python 3.14

## [0.1.1] - 2026-04-13

### Changed

- Expanded README with motivation, detailed guides for all concepts, caching/invalidation docs, reusable mixins pattern, and complete API reference tables

## [0.1.0] - 2025-04-12

### Added

- `Marker` base class — subclass to define markers with optional pydantic schema
- `MarkerGroup` — bundle related markers into a `.mixin` for clean inheritance
- `Registry` — track subclasses with `.subclasses()` and `.all` aggregation
- `MarkerInstance` — validated marker usage, works as both `Annotated[]` metadata and method decorator
- `MemberInfo` — unified metadata for fields and methods with `has`/`get`/`get_all` queries
- MRO-walking `Collector` with weakref-based per-class caching
- Intermediate marker base classes for shared schema fields
- `AllProxy` for cross-subclass collection via `Registry.all`
- PEP 561 `py.typed` marker
- 70 tests covering all features
- ORM-style real-world usage example with SQL generation
