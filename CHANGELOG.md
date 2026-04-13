# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
