"""TESTS ONLY: a tiny stand-in for FastAPI built on Starlette, so the real app can be served in a sandbox
that cannot install fastapi. It supports just what app/api.py uses. Production uses the real FastAPI."""
import inspect
import json
import re
from typing import Any, get_origin

from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount


class HTTPException(Exception):
    def __init__(self, status_code, detail=None):
        self.status_code, self.detail = status_code, detail


class _Dep:
    def __init__(self, fn):
        self.fn = fn


def Depends(fn):
    return _Dep(fn)


class _Header:
    def __init__(self, default=None):
        self.default = default


def Header(default=None):
    return _Header(default)


def _conv(v, ann):
    if v is None or ann in (inspect._empty, str, Any):
        return v
    base = ann
    if getattr(ann, "__origin__", None) is not None and type(None) in getattr(ann, "__args__", ()):
        base = [a for a in ann.__args__ if a is not type(None)][0]
    try:
        return base(v) if base in (int, float) else (v.lower() in ("1", "true") if base is bool else v)
    except Exception:
        raise HTTPException(422, "bad parameter")


class FastAPI:
    def __init__(self, **kw):
        self.routes, self.mw, self.handlers, self.startups, self.mounts = [], [], {}, [], []

    def mount(self, path, app, name=None):
        self.mounts.append(Mount(path, app=app, name=name))

    def middleware(self, kind):
        def deco(fn):
            self.mw.append(fn)
            return fn
        return deco

    def on_event(self, ev):
        def deco(fn):
            self.startups.append(fn)
            return fn
        return deco

    def exception_handler(self, exc):
        def deco(fn):
            self.handlers[exc] = fn
            return fn
        return deco

    def _route(self, method):
        def maker(path, **kw):
            def deco(fn):
                self.routes.append((method, path, fn))
                return fn
            return deco
        return maker

    def __getattr__(self, name):
        if name in ("get", "post", "put", "patch", "delete"):
            return self._route(name.upper())
        raise AttributeError(name)

    # ------------------------------------------------------------------ request handling
    async def _call(self, fn, request, cache, cleanup):
        sig, kwargs = inspect.signature(fn), {}
        hints = getattr(fn, "__annotations__", {})
        for name, p in sig.parameters.items():
            ann, d = hints.get(name, p.annotation), p.default
            if isinstance(d, _Dep):
                if d.fn not in cache:
                    cache[d.fn] = await self._call(d.fn, request, cache, cleanup)
                kwargs[name] = cache[d.fn]
            elif isinstance(d, _Header):
                kwargs[name] = request.headers.get(name.replace("_", "-"), d.default)
            elif ann is Request:
                kwargs[name] = request
            elif inspect.isclass(ann) and issubclass(ann, BaseModel):
                try:
                    kwargs[name] = ann(**(await request.json()))
                except Exception as e:
                    raise HTTPException(422, str(e))
            elif get_origin(ann) is dict or ann is dict:
                kwargs[name] = await request.json()
            elif name in request.path_params:
                kwargs[name] = _conv(request.path_params[name], ann)
            else:
                v = request.query_params.get(name)
                kwargs[name] = _conv(v, ann) if v is not None else (None if d is inspect._empty else d)
        out = fn(**kwargs)
        if inspect.isgenerator(out):
            val = next(out)
            cleanup.append(out)
            return val
        if inspect.iscoroutine(out):
            out = await out
        return out

    def build(self):
        async def endpoint_for(fn, request):
            cache, cleanup = {}, []
            try:
                try:
                    result = await self._call(fn, request, cache, cleanup)
                    for g in reversed(cleanup):
                        try:
                            next(g)
                        except StopIteration:
                            pass
                    cleanup.clear()
                except BaseException as exc:
                    for g in reversed(cleanup):
                        try:
                            g.throw(exc)
                        except BaseException:
                            pass
                    raise
            except HTTPException as e:
                return JSONResponse({"detail": e.detail}, status_code=e.status_code)
            except Exception as e:
                for typ, h in self.handlers.items():
                    if isinstance(e, typ):
                        return await h(request, e)
                raise
            if hasattr(result, "status_code") and hasattr(result, "headers"):
                return result
            return JSONResponse(result)

        routes = []
        for method, path, fn in self.routes:
            async def ep(request, fn=fn):
                return await endpoint_for(fn, request)
            routes.append(Route(path, ep, methods=[method]))
        app = Starlette(routes=routes + self.mounts)
        for fn in self.mw:
            async def dispatch(request, call_next, fn=fn):
                return await fn(request, call_next)
            from starlette.middleware.base import BaseHTTPMiddleware
            app.add_middleware(BaseHTTPMiddleware, dispatch=dispatch)
        for s in self.startups:
            s()
        return app

    async def __call__(self, scope, receive, send):
        if not hasattr(self, "_app"):
            self._app = self.build()
        await self._app(scope, receive, send)
