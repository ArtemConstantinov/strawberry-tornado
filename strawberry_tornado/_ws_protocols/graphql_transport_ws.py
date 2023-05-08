import asyncio
from datetime import timedelta
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Optional,
    final
)

from strawberry.schema import BaseSchema
from strawberry.subscriptions.protocols.graphql_transport_ws.handlers import (
    BaseGraphQLTransportWSHandler,
)
from strawberry.subscriptions.protocols.graphql_transport_ws.types import (
    SubscribeMessage,
)


class GraphQLTransportWSAdapter(BaseGraphQLTransportWSHandler):
    __slots__ = (
        "_get_context",
        "_get_root_value",
        "_send_json",
        "_close",
        "_keep_alive",
        "_keep_alive_interval",
        "_is_alive",
    )

    def __init__(
        self,
        schema: BaseSchema,
        debug: bool,
        connection_init_wait_timeout: timedelta,
        keep_alive: bool,
        keep_alive_interval: float,
        get_context: Callable[..., Coroutine[Any, Any, Any]],
        get_root_value: Callable[..., Coroutine[Any, Any, Any]],
        send_json: Callable[[Dict], Coroutine[Any, Any, None]],
        close: Callable[[int, Optional[str]], None]
    ) -> None:
        super().__init__(schema, debug, connection_init_wait_timeout)
        self._keep_alive = keep_alive
        self._keep_alive_interval = keep_alive_interval
        self._get_context = get_context
        self._get_root_value = get_root_value
        self._send_json = send_json
        self._close = close
        self._is_alive = asyncio.Event()
        self._is_alive.set()

    @final
    async def get_context(self) -> Any:
        ctx = await self._get_context()
        if isinstance(ctx, dict):
            ctx["connection_params"] = self.connection_params
        elif hasattr(ctx, "connection_params"):
            setattr(ctx, "connection_params", self.connection_params)
        return ctx

    @final
    async def get_root_value(self) -> Any:
        return await self._get_root_value()

    @final
    async def send_json(self, data: Dict) -> None:
        await self._send_json(data)

    @final
    async def close(self, code: int, reason: Optional[str] = None) -> None:
        self._close(code, reason)

    @final
    async def handle_request(self) -> None:
        return None

    def watch_pre_init_connection_timeout(self) -> None:
        timeout_handler = self.handle_connection_init_timeout()
        self.connection_init_timeout_task = asyncio.create_task(timeout_handler)

    @final
    async def cleanup(self) -> None:
        for operation_id in list(self.subscriptions.keys()):
            await self.cleanup_operation(operation_id)
        await self.reap_completed_tasks()
