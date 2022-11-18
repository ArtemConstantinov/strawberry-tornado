import asyncio
from http.client import (
    BAD_REQUEST,
    NOT_FOUND,
)
import json
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    Optional,
    Union,
    cast,
    final,
)
from strawberry.exceptions import MissingQueryError
from strawberry.http import (
    parse_request_data,
    process_result,
    GraphQLRequestData,
)
from strawberry.schema.exceptions import InvalidOperationTypeError
from strawberry.utils.graphiql import get_graphiql_html
from strawberry.utils.debug import pretty_print_graphql_operation
from strawberry.file_uploads.utils import replace_placeholders_with_files
from strawberry.types.graphql import OperationType

from ._base_resolver import GQLBaseResolver
if TYPE_CHECKING:
    from .handler import GraphQLHandler


__all__ = (
    "GQLHttpResolver",
)

CONTENT_JSON = "application/json"
CONTENT_FORM_DATA = "multipart/form-data"


class GQLHttpResolver(GQLBaseResolver):
    """Resolve Http GET/POST requests"""

    def should_render_graphiql(self, inst: "GraphQLHandler") -> bool:
        if not inst.graphiql:
            return False
        return any(
            supported_header in inst.request.headers.get("Accept", "")
            for supported_header in ("text/html", "*/*")
        )

    @final
    async def get(self, inst: "GraphQLHandler", *args: Any, **kwargs: Any) -> None:
        if self.should_render_graphiql(inst):
            template = get_graphiql_html()
            return await inst.finish(template)

        elif inst.request.arguments:
            query_data = _decode_query_data(inst)
            try:
                request_data = parse_request_data(query_data)
            except MissingQueryError:
                inst.set_status(BAD_REQUEST, "No GraphQL query found in the request")
                return await inst.finish()
            allowed_operation_types = (
                OperationType.from_http(inst.request.method or "GET")
                if inst.allow_queries_via_get else
                set()
            )
            response = await self.__execute(inst, request_data, allowed_operation_types)
            await inst.finish(response)

        inst.set_status(NOT_FOUND)
        return await inst.finish()

    @final
    async def post(self, inst: "GraphQLHandler", *args: Any, **kwargs: Any) -> None:
        try:
            req = _decode_request_data(inst, self.json_decoder)
        except json.JSONDecodeError:
            inst.set_status(BAD_REQUEST, "Unable to parse request body as JSON.")
            return await inst.finish()

        try:
            request_data = parse_request_data(req)
        except MissingQueryError:
            inst.set_status(BAD_REQUEST, "No valid query was provided for the request.")
            return await inst.finish()
        response = await self.__execute(inst, request_data)
        await inst.finish(response)

    async def __execute(self, inst: "GraphQLHandler", request_data: "GraphQLRequestData", allowed_operation_types: Optional[Iterable[OperationType]] = None) -> Optional[Union[str, bytes]]:  # noqa: E501
        context, root = await asyncio.gather(
            self.context_method(),
            self.root_value_method()
        )
        if inst.application.settings.get("debug", False):
            pretty_print_graphql_operation(
                request_data.operation_name,
                request_data.query,
                request_data.variables,
            )
        try:
            result = await inst.schema.execute(
                query=request_data.query,
                context_value=context,
                root_value=root,
                variable_values=request_data.variables,
                operation_name=request_data.operation_name,
                allowed_operation_types=allowed_operation_types,
            )
        except InvalidOperationTypeError as e:
            inst.set_status(BAD_REQUEST, e.as_http_error_reason(inst.request.method or ""))
            return None

        return self.json_encoder(
            cast(dict, process_result(result))
        )


def _decode_request_data(inst: "GraphQLHandler", json_decoder: Callable[[Union[str, bytes]], Dict]) -> Dict[str, Any]:
    content_type = inst.request.headers.get("content-type", "")
    if content_type.startswith(CONTENT_JSON):
        return json_decoder(inst.request.body)
    elif content_type.startswith(CONTENT_FORM_DATA):
        files = inst.request.files
        operations = json_decoder(cast(str, inst.get_body_argument("operations", "{}")))
        files_map = json_decoder(cast(str, inst.get_body_argument("map", "{}")))
        return replace_placeholders_with_files(operations, files_map, files)
    return {}


def _decode_query_data(inst: "GraphQLHandler") -> Dict[str, Any]:
    lookup_names = ("query", "variables", "operationName")
    values = (inst.get_query_argument(name, None) for name in lookup_names)
    return dict((k, v) for k, v in zip(lookup_names, values) if v is not None)
