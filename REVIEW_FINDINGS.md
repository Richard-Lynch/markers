# Library Review Findings & Enhancement Plan

## Review Process

7 independent review agents analyzed the `markers` library from different angles:

1. **ORM Framework Builder** - Attempted building a lightweight ORM
2. **Event System Builder** - Attempted building an event/hook system
3. **API/Serialization Builder** - Attempted building a REST API framework
4. **Type Safety Expert** - Audited all type stubs and generics
5. **API Design Alternatives** - Compared against attrs, pydantic, SQLAlchemy, Django patterns
6. **State Machine Usage** - Rewrote the real-world state machine example with new API
7. **Edge Cases & Robustness** - Audited error handling, edge cases, test coverage

## Top Cross-Review Themes

### 1. String-based marker lookup is error-prone (5/7 reviews)
`info.get("max_len")` typos silently return `None`. All reviewers want `info.get(MaxLen)`.

### 2. MarkerInstance lacks public introspection (3/7 reviews)
No `__eq__`, no `as_dict()`, `_params`/`_kwargs` are private. Blocks diff tools, serialization, OpenAPI generation.

### 3. Multiple mixin inheritance causes type checker noise (4/7 reviews)
`class User(DB.mixin, Validation.mixin): # type: ignore[misc]` — need `combine()`.

### 4. `collect_markers()` drops MemberInfo (3/7 reviews)
Loses `.owner`, callable reference. `collect()` should return rich type too.

### 5. `CollectResult` is unparameterized (2/7 reviews)
`dict[str, Any]` in type checkers. Should be generic for typed param access.

### 6. classmethod/staticmethod markers silently lost (2/7 reviews)
Collector doesn't unwrap descriptors. HIGH severity data loss.

## Enhancement Execution Plan

### E1: Parameterize `CollectResult` as `dict[str, MarkerInstance]`
### E2: Make `CollectResult` generic + `Self` in stubs
### E3: `MarkerGroup.combine(*groups)` helper
### E4: Accept `type[Marker]` in `MemberInfo.has()`/`.get()`
### E5: `MarkerInstance.__eq__`, `as_dict()`, `params` property
### E6: Proper `MISSING` sentinel with `__repr__`/`__bool__`
### E7: Unwrap classmethod/staticmethod/property in collector
### E8: `collect()` returns `CollectResult` (unify APIs)
### E9: `label` on `get_first()`, add `get_one_name()`/`get_first_name()`
### E10: `CollectResult.sorted_by(attr, reverse)`
### E11: Input validation on `collect()`/`collect_markers()`
### E12: Fix registry abstract intermediate registration
### E13: List-based marker group definition syntax
### E14: Improve `AllProxy.__repr__`
### E15: Truncate `get_one()` error for large results

## Rejected Items

- Decorator-based group registration — scatters group membership
- Functional marker syntax — loses dataclass_transform type checking
- `group_by()`/`to_dict()`/`apply()` on CollectResult — manual loops clearer
- MemberInfo.__getattr__ delegation — collides with real attributes
- Class-level markers — significant new concept, defer to future version
- Mypy plugin for dynamic descriptors — too much effort, promote collect() instead
