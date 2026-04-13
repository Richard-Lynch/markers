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

# Full matrix (Python 3.10–3.13)
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

## Release process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Commit: `git commit -am "Release v0.x.y"`
4. Tag: `git tag v0.x.y`
5. Push: `git push origin main --tags`

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
