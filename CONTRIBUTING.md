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
├── descriptors.py   # BaseMixin + descriptor classes
├── marker.py        # Marker + MarkerMeta
├── groups.py        # MarkerGroup + MarkerGroupMeta
└── registry.py      # Registry + AllProxy
```
