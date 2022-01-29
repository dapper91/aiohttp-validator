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
