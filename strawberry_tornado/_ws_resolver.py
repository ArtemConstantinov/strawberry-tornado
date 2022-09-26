import asyncio
from datetime import timedelta
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    Mapping,
    Protocol,
    Type,
    TypedDict,
    Optional,
    cast,
    final,
)

from strawberry.schema import BaseSchema
from strawberry.subscriptions import (
    GRAPHQL_TRANSPORT_WS_PROTOCOL,
    GRAPHQL_WS_PROTOCOL,
)
from ._ws_protocols.graphql_transport_ws import GraphQLTransportWSAdapter
from ._ws_protocols.graphql_ws import GraphQLWSAdapter
from ._base_resolver import GQLBaseResolver
if TYPE_CHECKING:
    from .handler import GraphQLHandler


class GqlProtocol(Protocol):
    def __init__(  # noqa: E704
        self,
        schema: BaseSchema,
        debug: bool,
        connection_init_wait_timeout: timedelta,
        keep_alive: bool,
        keep_alive_interval: float,
        get_context: Callable[..., Coroutine[Any, Any, Any]],
        get_root_value: Callable[..., Coroutine[Any, Any, Any]],
        send_json: Callable[[Mapping[str, Any]], Coroutine[Any, Any, None]],
        close: Callable[[int, Optional[str]], None],
    ) -> None: ...
    def watch_pre_init_connection_timeout(self) -> None: ...  # noqa: E704
    async def get_context(self) -> Any: ...  # noqa: E704
    async def get_root_value(self) -> Any: ...  # noqa: E704
    async def send_json(self, data: Mapping[str, Any]) -> None: ...  # noqa: E704
    async def close(self, code: int, reason: str) -> None: ...  # noqa: E704
    async def handle_request(self) -> Any: ...  # noqa: E704
    async def handle(self) -> Any: ...  # noqa: E704
    async def handle_connection_init_timeout(self): ...  # noqa: E704
    async def handle_message(self, message: Dict): ...  # noqa: E704
    async def cleanup(self) -> None: ...  # noqa: E704


class AdapterParams(TypedDict, total=False):
    schema: BaseSchema
    debug: bool
    connection_init_wait_timeout: timedelta
    keep_alive: bool
    keep_alive_interval: float
    get_context: Callable[..., Coroutine[Any, Any, Any]]
    get_root_value: Callable[..., Coroutine[Any, Any, Any]]
    send_json: Callable[[Mapping[str, Any]], Coroutine[Any, Any, None]]
    close: Callable[[int, Optional[str]], None]


class GQLWsResolver(GQLBaseResolver):
    """Resolve Web socket communication"""
    __slots__ = ("__protocol",)
    __protocol: GqlProtocol

    @final
    def select_subprotocol(self, subprotocols: list[str]) -> Optional[str]:
        if GRAPHQL_TRANSPORT_WS_PROTOCOL in subprotocols:
            return GRAPHQL_TRANSPORT_WS_PROTOCOL
        elif GRAPHQL_WS_PROTOCOL in subprotocols:
            return GRAPHQL_WS_PROTOCOL
        return None

    @final
    async def open(self, inst: "GraphQLHandler") -> None:
        if inst.get_status() >= 400:
            return inst.close(4500, "Internal server error.")

        if inst.selected_subprotocol is None:
            return inst.close(4400, "Bad request.")

        adpter_cls: Optional[Type[GqlProtocol]] = {
            GRAPHQL_TRANSPORT_WS_PROTOCOL: GraphQLTransportWSAdapter,
            GRAPHQL_WS_PROTOCOL: GraphQLWSAdapter,
        }.get(inst.selected_subprotocol)

        if adpter_cls is None:
            return inst.close(4406, "Subprotocol not acceptable.")

        async def write_msg(response: Mapping[str, Any]) -> None:
            data = self.json_encoder(cast(dict, response))
            await inst.write_message(data)

        params: AdapterParams = {
            "schema": inst.schema,
            "debug": inst.application.settings.get("debug", False),
            "connection_init_wait_timeout": inst.ws_connection_init_wait_timeout,
            "keep_alive": inst.ws_keep_alive,
            "keep_alive_interval": inst.ws_keep_alive_interval,
            "get_context": self.context_method,
            "get_root_value": self.root_value_method,
            "send_json": write_msg,
            "close": inst.close
        }
        self.__protocol = adpter_cls(**params)
        self.__protocol.watch_pre_init_connection_timeout()
        return None

    @final
    def on_close(self, inst: "GraphQLHandler") -> None:
        asyncio.create_task(self.__protocol.cleanup())

    @final
    async def on_message(self, inst: "GraphQLHandler", message: str) -> None:
        parsed_message = self.json_decoder(message)
        await self.__protocol.handle_message(parsed_message)
