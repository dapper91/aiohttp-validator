import pydantic as pd
from aiohttp import web
from aiohttp.pytest_plugin import AiohttpClient

from aiohttp_validator import validator


async def test_params(aiohttp_client: AiohttpClient):
    @validator.validated()
    async def test_method(request: web.Request, param1: int, param2: float):
        assert isinstance(request, web.Request)
        assert param1 == 1
        assert param2 == 3.14

        return web.Response(status=200)

    app = web.Application()
    app.router.add_get('/', test_method)

    client = await aiohttp_client(app)

    resp = await client.get('/', params=dict(param1='1', param2='3.14'))
    assert resp.status == 200


async def test_params_error(aiohttp_client: AiohttpClient):
    @validator.validated()
    async def test_method(request: web.Request, param: int):
        return web.Response(status=200)

    app = web.Application()
    app.router.add_get('/', test_method)

    client = await aiohttp_client(app)

    resp = await client.get('/', params=dict(param='abc'))
    assert resp.status == 400


async def test_headers__dict(aiohttp_client: AiohttpClient):
    @validator.validated()
    async def test_method(request: web.Request, headers: dict):
        assert isinstance(request, web.Request)
        assert headers['header1'] == '1'
        assert headers['header2'] == '3.14'

        return web.Response(status=200)

    app = web.Application()
    app.router.add_get('/', test_method)

    client = await aiohttp_client(app)

    resp = await client.get('/', headers=dict(header1='1', header2='3.14'))
    assert resp.status == 200


async def test_headers__model(aiohttp_client: AiohttpClient):
    class Headers(pd.BaseModel):
        header1: int
        header2: float

    @validator.validated()
    async def test_method(request: web.Request, headers: Headers):
        assert isinstance(request, web.Request)
        assert headers == Headers(header1=1, header2=3.14)

        return web.Response(status=200)

    app = web.Application()
    app.router.add_get('/', test_method)

    client = await aiohttp_client(app)

    resp = await client.get('/', headers=dict(header1='1', header2='3.14'))
    assert resp.status == 200


async def test_headers__model_error(aiohttp_client: AiohttpClient):
    class Headers(pd.BaseModel):
        header: int

    @validator.validated()
    async def test_method(request: web.Request, headers: Headers):
        return web.Response(status=200)

    app = web.Application()
    app.router.add_get('/', test_method)

    client = await aiohttp_client(app)

    resp = await client.get('/', headers=dict(header='abc'))
    assert resp.status == 400


async def test_cookies__dict(aiohttp_client: AiohttpClient):
    @validator.validated()
    async def test_method(request: web.Request, cookies: dict):
        assert isinstance(request, web.Request)
        assert cookies == dict(cookie1='1', cookie2='3.14')

        return web.Response(status=200)

    app = web.Application()
    app.router.add_get('/', test_method)

    client = await aiohttp_client(app)

    resp = await client.get('/', cookies=dict(cookie1='1', cookie2='3.14'))
    assert resp.status == 200


async def test_cookies__model(aiohttp_client: AiohttpClient):
    class Cookies(pd.BaseModel):
        cookie1: int
        cookie2: float

    @validator.validated()
    async def test_method(request: web.Request, cookies: Cookies):
        assert isinstance(request, web.Request)
        assert cookies == Cookies(cookie1=1, cookie2=3.14)

        return web.Response(status=200)

    app = web.Application()
    app.router.add_get('/', test_method)

    client = await aiohttp_client(app)

    resp = await client.get('/', cookies=dict(cookie1='1', cookie2='3.14'))
    assert resp.status == 200


async def test_cookies__model_error(aiohttp_client: AiohttpClient):
    class Cookies(pd.BaseModel):
        cookie: int

    @validator.validated()
    async def test_method(request: web.Request, cookies: Cookies):
        return web.Response(status=200)

    app = web.Application()
    app.router.add_get('/', test_method)

    client = await aiohttp_client(app)

    resp = await client.get('/', cookies=dict(cookie='abc'))
    assert resp.status == 400


async def test_body__str(aiohttp_client: AiohttpClient):
    @validator.validated()
    async def test_method(request: web.Request, body: str):
        assert isinstance(request, web.Request)
        assert body == 'hello'

        return web.Response(status=200)

    app = web.Application()
    app.router.add_get('/', test_method)

    client = await aiohttp_client(app)

    resp = await client.get('/', data='hello')
    assert resp.status == 200


async def test_body__bytes(aiohttp_client: AiohttpClient):
    @validator.validated()
    async def test_method(request: web.Request, body: bytes):
        assert isinstance(request, web.Request)
        assert body == b'hello'

        return web.Response(status=200)

    app = web.Application()
    app.router.add_get('/', test_method)

    client = await aiohttp_client(app)

    resp = await client.get('/', data='hello')
    assert resp.status == 200


async def test_body__dict(aiohttp_client: AiohttpClient):
    @validator.validated()
    async def test_method(request: web.Request, body: dict):
        assert isinstance(request, web.Request)
        assert body == {'field1': 1, 'field2': 3.14}

        return web.Response(status=200)

    app = web.Application()
    app.router.add_get('/', test_method)

    client = await aiohttp_client(app)

    resp = await client.get('/', json={'field1': 1, 'field2': 3.14})
    assert resp.status == 200


async def test_body__model(aiohttp_client: AiohttpClient):
    class Body(pd.BaseModel):
        field1: int
        field2: float

    @validator.validated()
    async def test_method(request: web.Request, body: Body):
        assert isinstance(request, web.Request)
        assert body == Body(field1=1, field2=3.14)

        return web.Response(status=200)

    app = web.Application()
    app.router.add_get('/', test_method)

    client = await aiohttp_client(app)

    resp = await client.get('/', json={'field1': 1, 'field2': 3.14})
    assert resp.status == 200


async def test_body__model_error(aiohttp_client: AiohttpClient):
    class Body(pd.BaseModel):
        field: int

    @validator.validated()
    async def test_method(request: web.Request, body: Body):
        return web.Response(status=200)

    app = web.Application()
    app.router.add_get('/', test_method)

    client = await aiohttp_client(app)

    resp = await client.get('/', json={'field': 'abc'})
    assert resp.status == 422
