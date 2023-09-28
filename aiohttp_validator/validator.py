import functools as ft
import inspect
import json
import typing
from collections import defaultdict
from typing import Any, Callable, Coroutine, Dict, List, Mapping, NamedTuple, Optional, Type, Union

import multidict
import pydantic
from aiohttp import web


class FuncAnnotation(NamedTuple):
    body: Any
    headers: Any
    cookies: Any
    params: Dict[str, Any]


def extract_annotations(
        func: Callable[..., Any],
        body_argname: Optional[str] = None,
        headers_argname: Optional[str] = None,
        cookies_argname: Optional[str] = None,
) -> FuncAnnotation:
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

    return FuncAnnotation(
        body=body_annotation,
        headers=headers_annotation,
        cookies=cookies_annotation,
        params=params_annotations,
    )


def multidict_to_dict(mdict: multidict.MultiMapping[str]) -> Mapping[str, List[str]]:
    dct = defaultdict(list)
    for key, value in mdict.items():
        dct[key].append(value)

    return dct


def fit_multidict_to_model(
        mdict: multidict.MultiMapping[str],
        model: Type[pydantic.BaseModel],
) -> Mapping[str, Union[str, List[str]]]:
    dct = multidict_to_dict(mdict)

    fitted: Dict[str, Union[str, List[str]]] = {}
    for key, value in dct.items():
        field = model.model_fields.get(key)
        if field is None:
            fitted[key] = value
        else:
            collection_types = (list, tuple)
            if field.annotation in collection_types or typing.get_origin(field.annotation) in collection_types:
                fitted[key] = value
            else:
                fitted[key] = value[0]

    return fitted


BodyType = Union[str, bytes, Dict[Any, Any], pydantic.BaseModel]


async def process_body(request: web.Request, body_annotation: Any) -> BodyType:
    try:
        body_type = typing.get_origin(body_annotation) or body_annotation

        body: BodyType
        if issubclass(body_type, str):
            body = await request.text()
        elif issubclass(body_type, bytes):
            body = await request.read()
        elif issubclass(body_type, dict):
            body = await request.json()
        elif issubclass(body_type, pydantic.BaseModel):
            try:
                body = body_type.model_validate(await request.json())
            except pydantic.ValidationError:
                raise web.HTTPUnprocessableEntity
        else:
            raise AssertionError("unprocessable body type")

    except (json.JSONDecodeError, UnicodeDecodeError):
        raise web.HTTPBadRequest

    return body


HeaderType = Union[Mapping[str, str], pydantic.BaseModel]


async def process_headers(request: web.Request, headers_annotation: Any) -> HeaderType:
    headers_type = typing.get_origin(headers_annotation) or headers_annotation
    if issubclass(headers_type, dict):
        headers = request.headers
    elif issubclass(headers_type, pydantic.BaseModel):
        fitted_headers = fit_multidict_to_model(request.headers, headers_type)
        try:
            headers = headers_type.model_validate(fitted_headers)
        except pydantic.ValidationError:
            raise web.HTTPBadRequest
    else:
        raise AssertionError("unprocessable headers type")

    return headers


CookiesType = Union[Mapping[str, str], pydantic.BaseModel]


async def process_cookes(request: web.Request, cookies_annotation: Any) -> CookiesType:
    cookies_type = typing.get_origin(cookies_annotation) or cookies_annotation
    if issubclass(cookies_type, dict):
        cookies = request.cookies
    elif issubclass(cookies_type, pydantic.BaseModel):
        try:
            cookies = cookies_type.model_validate(request.cookies)
        except pydantic.ValidationError:
            raise web.HTTPBadRequest
    else:
        raise AssertionError("unprocessable cookies type")

    return cookies


FuncType = Callable[..., Coroutine[Any, Any, web.StreamResponse]]


def validated(
        config: Optional[pydantic.ConfigDict] = None,
        body_argname: Optional[str] = 'body',
        headers_argname: Optional[str] = 'headers',
        cookies_argname: Optional[str] = 'cookies',
) -> Callable[[FuncType], FuncType]:
    """
    Creates a function validating decorator.

    If any path or query parameter name are clashes with body, headers or cookies argument for some reason
    the last can be renamed. If any argname is `None` the corresponding request part will not be passed to the function
    and argname can be used as a path or query parameter.

    :param config: pydantic config
    :param body_argname: argument name the request body is passed by
    :param headers_argname: argument name the request headers is passed by
    :param cookies_argname: argument name the request cookies is passed by

    :return: decorator
    """

    def decorator(func: FuncType) -> FuncType:
        annotations = extract_annotations(func, body_argname, headers_argname, cookies_argname)

        params_model: Type[pydantic.BaseModel] = \
            pydantic.create_model(
                'Params',
                __config__=config,
                **annotations.params,
            )

        @ft.wraps(func)
        async def wrapper(request: web.Request, *args: Any, **kwargs: Any) -> web.StreamResponse:
            fitted_query = fit_multidict_to_model(request.query, params_model)
            try:
                params = params_model.model_validate(dict(fitted_query, **request.match_info))
            except pydantic.ValidationError:
                raise web.HTTPBadRequest

            kwargs.update(params.model_dump())
            if body_argname and annotations.body is not None:
                kwargs[body_argname] = await process_body(request, annotations.body)
            if headers_argname and annotations.headers is not None:
                kwargs[headers_argname] = await process_headers(request, annotations.headers)
            if cookies_argname and annotations.cookies is not None:
                kwargs[cookies_argname] = await process_cookes(request, annotations.cookies)

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
