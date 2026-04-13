from collections.abc import Callable
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel
from typing_extensions import Self, dataclass_transform

from markers._types import CollectResult, MemberInfo

_F = TypeVar("_F", bound=Callable[..., Any])

@dataclass_transform()
class MarkerMeta(type):
    _mark_name: str
    _schema_model: type[BaseModel] | None
    _schema_annotations: dict[str, Any]
    _schema_defaults: dict[str, Any]

class Marker(metaclass=MarkerMeta):
    _mark_name: ClassVar[str]
    _schema_model: ClassVar[type[BaseModel] | None]
    _schema_annotations: ClassVar[dict[str, Any]]
    _schema_defaults: ClassVar[dict[str, Any]]
    mark: ClassVar[str]
    marker_name: ClassVar[str]
    def __call__(self, fn: _F) -> _F: ...
    def __getattr__(self, key: str) -> Any: ...
    def as_dict(self) -> dict[str, Any]: ...
    @classmethod
    def collect(cls, target: type) -> dict[str, MemberInfo]: ...
    @classmethod
    def collect_markers(cls, target: type) -> CollectResult[Self]: ...
    @classmethod
    def invalidate(cls, target: type) -> None: ...
