
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Optional,
    Union,
    Callable,
    Coroutine,
)
if TYPE_CHECKING:
    from .handler import GraphQLHandler


@dataclass
class GQLBaseResolver:
    __slots__ = ()
    context_method: Callable[..., Coroutine[Any, Any, Any]]
    root_value_method: Callable[..., Coroutine[Any, Any, Any]]
    json_encoder: Callable[[Dict], Union[str, bytes]]
    json_decoder: Callable[[Union[str, bytes]], Dict]

    async def get(self, inst: "GraphQLHandler", *args: Any, **kwargs: Any) -> None:
        return None

    async def post(self, inst: "GraphQLHandler", *args: Any, **kwargs: Any) -> None:
        return None

    def select_subprotocol(self, subprotocols: list[str]) -> Optional[str]:
        return None

    async def open(self, inst: "GraphQLHandler") -> None:
        return None

    def on_close(self, inst: "GraphQLHandler") -> None:
        return None

    async def on_message(self, inst: "GraphQLHandler", message: str) -> None:
        return None
