# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
