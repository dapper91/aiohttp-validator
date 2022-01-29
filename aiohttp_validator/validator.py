import functools as ft
import inspect
import json
import typing
from collections import defaultdict
from typing import Any, Callable, Collection, Dict, Type

import multidict
import pydantic
from aiohttp import web


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


def validated(body_argname: str = 'body', headers_argname: str = 'headers') -> Callable:
    def decorator(func: Callable) -> Callable:
        body_annotation, headers_annotation = None, None
        params_model, params_annotations = None, {}

        signature = inspect.signature(func)

        # skip aiohttp method first argument (aiohttp.web.Request)
        parameters = list(signature.parameters.values())[1:]
        for param in parameters:
            if param.name == body_argname:
                body_annotation = param.annotation
            elif param.name == headers_argname:
                headers_annotation = param.annotation
            else:
                params_annotations[param.name] = (
                    param.annotation if param.annotation is not inspect.Parameter.empty else Any,
                    param.default if param.default is not inspect.Parameter.empty else ...,
                )

        params_model = pydantic.create_model('Params', **params_annotations)

        @ft.wraps(func)
        async def wrapper(request: web.Request, *args, **kwargs) -> Any:
            if body_annotation is not None:
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

                kwargs[body_argname] = body

            if headers_annotation is not None:
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

                kwargs[headers_argname] = headers

            fitted_query = fit_multidict_to_model(request.query, params_model)
            try:
                params = params_model.parse_obj(dict(fitted_query, **request.match_info))
            except pydantic.ValidationError:
                raise web.HTTPBadRequest

            kwargs.update(params.dict())

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
