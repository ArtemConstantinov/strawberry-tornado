# Strawberry Tornado

Strawberry Tornado is an strawberry-graphql Request handler for Tornado Web framework.


## Installation
``` Shell
> pip install git+https://github.com/ArtemConstantinov/strawberry-tornado.git
```

## Usage


``` Python
import asyncio
import strawberry
import tornado.web
from strawberry_tornado import GraphQLHandler



@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello World"


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def count(self, target: int = 10) -> AsyncGenerator[int, None]:
        for i in range(target):
            yield i
            await asyncio.sleep(0.5)


SCHEMA = strawberry.Schema(
    query=Query,
    subscription=Subscription,
)

class MyGQLHandler(GraphQLHandler):
    async def get_context(self) -> Any:
        return {"request": self.request}

    async def get_root_value(self) -> Any:
        return None

def make_app():
    return tornado.web.Application([
        (r"/graphql", MyGQLHandler, dict(schema=SCHEMA, graphiql=True)),
    ])

async def main():
    app = make_app()
    app.listen(8888)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```