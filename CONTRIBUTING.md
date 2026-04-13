# Contributing

## Setup

```bash
git clone https://github.com/Richard-Lynch/markers.git
cd markers
make venv
make deps
```

## Development workflow

### Run tests

```bash
# Quick run
make test

# With coverage
make test:cov

# Full matrix (Python 3.10–3.14)
tox
```

### Lint and format

```bash
# Check
make lint

# Auto-fix
make format
```

### Type check

```bash
make typecheck
```

### Run all checks

```bash
make check
```

## Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **Patch** (0.1.x): Bug fixes, documentation, CI changes
- **Minor** (0.x.0): New features, new Python version support, backwards-compatible changes
- **Major** (x.0.0): Breaking API changes

## Release process

`main` is protected — all changes go through pull requests.

1. Create a release branch: `git checkout -b release/v0.x.y`
2. Update version in `pyproject.toml`
3. Update `CHANGELOG.md`
4. Open a PR, get CI green, merge
5. Tag main: `git checkout main && git pull && git tag v0.x.y && git push origin v0.x.y`

The GitHub Actions release workflow will automatically:
- Run all checks
- Build sdist + wheel
- Publish to TestPyPI
- Publish to PyPI
- Create a GitHub Release with auto-generated notes

## Project structure

```
src/markers/
├── __init__.py      # Public API exports
├── _types.py        # MarkerInstance, MemberInfo, MemberKind, MISSING
├── core.py          # Collector — MRO walking + caching
├── descriptors.py   # BaseMixin, BaseMixinMeta + descriptor classes
├── marker.py        # Marker + MarkerMeta
├── marker.pyi       # Type stub — dataclass_transform for marker kwargs
├── groups.py        # MarkerGroup + MarkerGroupMeta
├── groups.pyi       # Type stub — mixin base class typing
├── registry.py      # Registry + AllProxy
└── py.typed         # PEP 561 marker
```

## Type stubs

The library uses `.pyi` stubs for `marker.py` and `groups.py` to provide
type information that can't be expressed inline:

- **`marker.pyi`** — Uses PEP 681 `dataclass_transform` on `MarkerMeta` so
  type checkers validate marker constructor kwargs against the schema
  annotations on each `Marker` subclass. Also exposes `__call__` and
  `__getattr__` on `Marker` instances for decorator and attribute access.

- **`groups.pyi`** — Declares `MarkerGroup.mixin = BaseMixin` so type checkers
  accept `class User(DB.mixin):` as valid and know the class inherits
  `BaseMixin`'s typed `.fields`, `.methods`, `.members` descriptors.

When modifying `marker.py` or `groups.py`, check that the corresponding
`.pyi` stub stays in sync.
