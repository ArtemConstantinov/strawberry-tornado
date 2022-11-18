import asyncio
from contextlib import suppress
from datetime import timedelta
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Optional,
    cast,
    final
)

from strawberry.schema import BaseSchema
from strawberry.subscriptions.protocols.graphql_ws.handlers import BaseGraphQLWSHandler
from strawberry.subscriptions.protocols.graphql_ws.types import OperationMessage


class GraphQLWSAdapter(BaseGraphQLWSHandler):
    __slots__ = (
        "_get_context",
        "_get_root_value",
        "_send_json"
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
        super().__init__(schema, debug, keep_alive, keep_alive_interval)
        self.connection_init_wait_timeout = connection_init_wait_timeout
        self.connection_init_timeout_task: Optional[asyncio.Task] = None
        self._get_context = get_context
        self._get_root_value = get_root_value
        self._send_json = send_json
        self._close = close

        self.connection_init_received = False

    @final
    async def get_context(self) -> Any:
        return await self._get_context()

    @final
    async def get_root_value(self) -> Any:
        return await self._get_root_value()

    @final
    async def send_json(self, data: OperationMessage) -> None:
        await self._send_json(cast(dict, data))

    @final
    async def close(self, code: int = 1000, reason: Optional[str] = None) -> None:
        self._close(code, reason)

    @final
    async def handle_request(self) -> None:
        return None

    @final
    def watch_pre_init_connection_timeout(self) -> None:
        timeout_handler = self.handle_connection_init_timeout()
        self.connection_init_timeout_task = asyncio.create_task(timeout_handler)

    @final
    async def handle_connection_init(self, message: OperationMessage) -> None:
        self.connection_init_received = True
        await super().handle_connection_init(message)

    @final
    async def cleanup(self) -> None:
        if self.keep_alive_task:
            self.keep_alive_task.cancel()
            with suppress(BaseException):
                await self.keep_alive_task

        for operation_id in list(self.subscriptions.keys()):
            await self.cleanup_operation(operation_id)

    @final
    async def handle_connection_init_timeout(self):
        delay = self.connection_init_wait_timeout.total_seconds()
        await asyncio.sleep(delay=delay)

        if self.connection_init_received:
            return

        reason = "Connection initialisation timeout"
        await self.close(code=4408, reason=reason)
