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
import datetime as dt
from uuid import UUID
from typing import Any, Dict, List

import pydantic
from aiohttp import web

import aiohttp_validator as validator

routes = web.RouteTableDef()


@routes.get('/posts')
@validator.validated()
async def get_posts(request: web.Request, tags: List[str], limit: pydantic.conint(gt=0, le=100), offset: int = 0):
    assert isinstance(tags, list)
    assert isinstance(limit, int)
    assert isinstance(offset, int)
    # your code here ...

    return web.Response(status=200)


class RequestHeaders(pydantic.BaseModel):
    requestId: int


class User(pydantic.BaseModel):
    name: str
    surname: str


class Post(pydantic.BaseModel):
    title: str
    text: str
    timestamp: float
    author: User
    tags: List[str] = pydantic.Field(default_factory=list)


@routes.post('/posts/{section}/{date}')
@validator.validated()
async def create_post(request: web.Request, body: Post, headers: RequestHeaders, section: str, date: dt.date):
    assert isinstance(body, Post)
    assert isinstance(headers, RequestHeaders)
    assert isinstance(date, dt.date)
    assert isinstance(section, str)
    # your code here ...

    return web.Response(status=201)


class AuthCookies(pydantic.BaseModel):
    tokenId: UUID


@routes.post('/users')
@validator.validated()
async def create_user(request: web.Request, body: Dict[str, Any], headers: RequestHeaders, cookies: AuthCookies):
    assert isinstance(body, dict)
    assert isinstance(headers, RequestHeaders)
    assert isinstance(cookies, AuthCookies)
    # your code here ...

    return web.Response(status=201)

app = web.Application()
app.add_routes(routes)

web.run_app(app, port=8080)

```

If any path or query parameter name are clashes with body, headers or cookies argument 
for some reason the last can be renamed:

```py
@routes.post('/{cookies}')
@validator.validated(cookies_argname='_cookies')
async def method(request: web.Request, body: Dict[str, Any], _cookies: AuthCookies, cookies: str):
    # your code here ...

    return web.Response(status=201)
```

If any argname is `None` the corresponding request part will not be passed to the function
and argname can be used as a path or query parameter.

```py
@routes.post('/{body}/{headers}')
@validator.validated(body_argname=None, headers_argname=None, cookies_argname=None)
async def method(request: web.Request, body: str, headers: str, cookies: str = ''):
    # your code here ...

    return web.Response(status=201)
```
