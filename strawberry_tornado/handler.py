from __future__ import annotations
from datetime import timedelta
import json
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Protocol,
    Tuple,
    Union,
    Optional,
    final
)

import tornado.websocket
from strawberry.schema import BaseSchema
from strawberry.subscriptions import (
    GRAPHQL_TRANSPORT_WS_PROTOCOL,
    GRAPHQL_WS_PROTOCOL,
)
from ._base_resolver import GQLBaseResolver
from ._http_resolver import GQLHttpResolver
from ._ws_resolver import GQLWsResolver


class RequestResolver(Protocol):
    async def get(self, inst, *args: Any, **kwargs: Any) -> None: ...  # noqa: E704
    async def post(self, inst, *args: Any, **kwargs: Any) -> None: ...  # noqa: E704
    def select_subprotocol(self, subprotocols: list[str]) -> Optional[str]: ...  # noqa: E704
    async def open(self, inst) -> None: ...  # noqa: E704
    def on_close(self, inst,) -> None: ...  # noqa: E704
    async def on_message(self, inst, message: str) -> None: ...  # noqa: E704
    def use_context_method(self, method: Callable[..., Coroutine[Any, Any, Any]]) -> None: ...  # noqa: E704
    def use_root_value_method(self, method: Callable[..., Coroutine[Any, Any, Any]]) -> None: ...  # noqa: E704
    def use_json_encoder(self, method: Callable[[Dict], Union[str, bytes]]) -> None: ...  # noqa: E704
    def use_json_decoder(self, method: Callable[[Union[str, bytes]], Dict]) -> None: ...  # noqa: E704


class GraphQLHandler(tornado.websocket.WebSocketHandler):
    __resolver: GQLBaseResolver
    schema: BaseSchema
    graphiql: bool
    allow_queries_via_get: bool
    ws_keep_alive: bool
    ws_keep_alive_interval: float
    ws_subscription_protocols: Tuple[str, ...]
    ws_connection_init_wait_timeout: timedelta

    __slots__ = (
        "schema",
        "graphiql",
        "allow_queries_via_get",
        "ws_keep_alive",
        "ws_keep_alive_interval",
        "ws_subscription_protocols",
        "ws_connection_init_wait_timeout",
    )

    @final
    def initialize(
        self,
        schema: BaseSchema,
        graphiql: bool = True,
        allow_queries_via_get: bool = True,
        ws_keep_alive: bool = False,
        ws_keep_alive_interval: float = 1,
        ws_subscription_protocols: Tuple[str, ...] = (GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL,),
        ws_connection_init_wait_timeout: timedelta = timedelta(minutes=1),
    ) -> None:
        self.schema = schema
        self.graphiql = graphiql
        self.allow_queries_via_get = allow_queries_via_get
        self.ws_keep_alive = ws_keep_alive
        self.ws_keep_alive_interval = ws_keep_alive_interval
        self.ws_subscription_protocols = ws_subscription_protocols
        self.ws_connection_init_wait_timeout = ws_connection_init_wait_timeout

    async def prepare(self) -> None:
        resolver_type = GQLWsResolver if self._is_ws else GQLHttpResolver
        self.__resolver = resolver_type(
            context_method=self.get_context,
            root_value_method=self.get_root_value,
            json_encoder=self.json_encoder,
            json_decoder=self.json_decoder,
        )

    @property
    def _is_ws(self) -> bool:
        return self.request.headers.get("Upgrade", "").lower() == "websocket"

    @final
    async def get(self, *args: Any, **kwargs: Any) -> None:
        get_method = (
            super().get
            if self._is_ws else
            self.__resolver.get
        )
        return await get_method(self, *args, **kwargs)

    @final
    async def post(self, *args: Any, **kwargs: Any) -> None:
        return await self.__resolver.post(self, *args, **kwargs)

    @final
    def select_subprotocol(self, subprotocols: list[str]) -> Optional[str]:
        return self.__resolver.select_subprotocol(subprotocols)

    @final
    async def open(self, *args: str, **kwargs: str) -> None:
        return await self.__resolver.open(self)

    @final
    def on_close(self) -> None:
        return self.__resolver.on_close(self)

    @final
    async def on_message(self, message: str) -> None:
        return await self.__resolver.on_message(self, message)

    async def get_context(self) -> Any:
        return None

    async def get_root_value(self) -> Any:
        return None

    def json_encoder(self, data: Dict) -> Union[str, bytes]:
        return json.dumps(data)

    def json_decoder(self, data: Union[str, bytes]) -> Dict:
        return json.loads(data)
