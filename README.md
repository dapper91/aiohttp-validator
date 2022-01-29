# aiohttp-validator

[![Downloads][download-badge]][download-url]
[![License][licence-badge]][licence-url]
[![Python Versions][python-version-badge]][python-version-url]

[download-badge]: https://static.pepy.tech/personalized-badge/aiohttp-validator?period=month&units=international_system&left_color=grey&right_color=orange&left_text=Downloads/month
[download-url]: https://pepy.tech/project/aiohttp-validator
[licence-badge]: https://img.shields.io/badge/license-Unlicense-blue.svg
[licence-url]: https://github.com/dapper91/aiohttp-validator/blob/master/LICENSE
[python-version-badge]: https://img.shields.io/pypi/pyversions/aiohttp-validator.svg
[python-version-url]: https://pypi.org/project/aiohttp-validator


aiohttp simple pydantic http request validator


## Installation

```shell
pip install aiohttp-validator
```


## A Simple Example

```py
from typing import Any, Dict, List

import pydantic
from aiohttp import web

import aiohttp_validator as validator

routes = web.RouteTableDef()


class RequestHeaders(pydantic.BaseModel):
    requestId: str
    timestamp: float = 0.0


@routes.get('/')
@validator.validated()
async def simple_get(request: web.Request, headers: RequestHeaders, offset: int = 0):
    assert isinstance(headers, RequestHeaders)
    assert isinstance(offset, int)

    return web.Response()


@routes.post('/{path}')
@validator.validated()
async def simple_post(request: web.Request, body: Dict[str, Any], path: str, offset: int, limit: int = 10):
    assert isinstance(body, dict)
    assert isinstance(path, str)
    assert isinstance(offset, int)
    assert isinstance(limit, int)

    return web.Response()


class SubModel(pydantic.BaseModel):
    l: List[str]
    i: int


class Body(pydantic.BaseModel):
    i: int
    f: float
    sub: SubModel


@routes.post('/{path1}/{path2}')
@validator.validated()
async def pydantic_body(request: web.Request, body: Body, path1: str, path2: int, pages: List[int]):
    assert isinstance(body, Body)
    assert isinstance(path1, str)
    assert isinstance(path2, int)
    assert isinstance(pages, list)

    return web.Response()


app = web.Application()
app.add_routes(routes)

web.run_app(app, port=8080)

```