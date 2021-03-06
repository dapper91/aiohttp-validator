import functools as ft
import inspect
import json
import typing
from collections import defaultdict
from types import SimpleNamespace
from typing import Any, Callable, Collection, Dict, Optional, Type

import multidict
import pydantic
from aiohttp import web


def extract_annotations(
        func: Callable,
        body_argname: Optional[str] = None,
        headers_argname: Optional[str] = None,
        cookies_argname: Optional[str] = None,
) -> SimpleNamespace:
    body_annotation, headers_annotation, cookies_annotation, params_annotations = None, None, None, {}

    signature = inspect.signature(func)

    # skip aiohttp method first argument (aiohttp.web.Request)
    parameters = list(signature.parameters.values())[1:]
    for param in parameters:
        if body_argname and param.name == body_argname:
            body_annotation = param.annotation
        elif headers_argname and param.name == headers_argname:
            headers_annotation = param.annotation
        elif cookies_argname and param.name == cookies_argname:
            cookies_annotation = param.annotation
        else:
            params_annotations[param.name] = (
                param.annotation if param.annotation is not inspect.Parameter.empty else Any,
                param.default if param.default is not inspect.Parameter.empty else ...,
            )

    return SimpleNamespace(
        body=body_annotation,
        headers=headers_annotation,
        cookies=cookies_annotation,
        params=params_annotations,
    )


def multidict_to_dict(mdict: multidict.MultiMapping) -> Dict[str, Any]:
    dct = defaultdict(list)
    for key, value in mdict.items():
        dct[key].append(value)

    return dct


def fit_multidict_to_model(mdict: multidict.MultiMapping, model: Type[pydantic.BaseModel]) -> Dict[str, Any]:
    dct = multidict_to_dict(mdict)

    fitted = {}
    for key, value in dct.items():
        field = model.__fields__.get(key)
        if field is None:
            fitted[key] = value
        else:
            field_type = typing.get_origin(field.outer_type_) or field.type_
            if inspect.isclass(field_type) and issubclass(field_type, (str, bytes, bytearray)):
                fitted[key] = value[0]
            elif issubclass(field_type, Collection):
                fitted[key] = value
            else:
                fitted[key] = value[0]

    return fitted


async def process_body(request: web.Request, body_annotation: Any) -> Any:
    try:
        body_type = typing.get_origin(body_annotation) or body_annotation
        if issubclass(body_type, str):
            body = await request.text()
        elif issubclass(body_type, bytes):
            body = await request.read()
        elif issubclass(body_type, dict):
            body = await request.json()
        elif issubclass(body_type, pydantic.BaseModel):
            try:
                body = body_type.parse_obj(await request.json())
            except pydantic.ValidationError:
                raise web.HTTPUnprocessableEntity
        else:
            raise AssertionError("unprocessable body type")

    except (json.JSONDecodeError, UnicodeDecodeError):
        raise web.HTTPBadRequest

    return body


async def process_headers(request: web.Request, headers_annotation: Any) -> Any:
    headers_type = typing.get_origin(headers_annotation) or headers_annotation
    if issubclass(headers_type, dict):
        headers = request.headers
    elif issubclass(headers_type, pydantic.BaseModel):
        fitted_headers = fit_multidict_to_model(request.headers, headers_type)
        try:
            headers = headers_type.parse_obj(fitted_headers)
        except pydantic.ValidationError:
            raise web.HTTPBadRequest
    else:
        raise AssertionError("unprocessable headers type")

    return headers


async def process_cookes(request: web.Request, cookies_annotation: Any) -> Any:
    cookies_type = typing.get_origin(cookies_annotation) or cookies_annotation
    if issubclass(cookies_type, dict):
        cookies = request.cookies
    elif issubclass(cookies_type, pydantic.BaseModel):
        try:
            cookies = cookies_type.parse_obj(request.cookies)
        except pydantic.ValidationError:
            raise web.HTTPBadRequest
    else:
        raise AssertionError("unprocessable cookies type")

    return cookies


def validated(
        body_argname: Optional[str] = 'body',
        headers_argname: Optional[str] = 'headers',
        cookies_argname: Optional[str] = 'cookies',
) -> Callable:
    """
    Creates a function validating decorator.

    If any path or query parameter name are clashes with body, headers or cookies argument for some reason
    the last can be renamed. If any argname is `None` the corresponding request part will not be passed to the function
    and argname can be used as a path or query parameter.

    :param body_argname: argument name the request body is passed by
    :param headers_argname: argument name the request headers is passed by
    :param cookies_argname: argument name the request cookies is passed by

    :return: decorator
    """

    def decorator(func: Callable) -> Callable:
        annotations = extract_annotations(func, body_argname, headers_argname, cookies_argname)

        params_model = pydantic.create_model('Params', **annotations.params)

        @ft.wraps(func)
        async def wrapper(request: web.Request, *args, **kwargs) -> Any:
            fitted_query = fit_multidict_to_model(request.query, params_model)
            try:
                params = params_model.parse_obj(dict(fitted_query, **request.match_info))
            except pydantic.ValidationError:
                raise web.HTTPBadRequest

            kwargs.update(params.dict())
            if body_argname and annotations.body is not None:
                kwargs[body_argname] = await process_body(request, annotations.body)
            if headers_argname and annotations.headers is not None:
                kwargs[headers_argname] = await process_headers(request, annotations.headers)
            if cookies_argname and annotations.cookies is not None:
                kwargs[cookies_argname] = await process_cookes(request, annotations.cookies)

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
