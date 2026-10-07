"""Minimal stand-ins for fastapi / pydantic so the route functions in app/api.py can be imported and called directly
(the real packages are not installed in every environment). Only used by tests."""
import sys
import types


class HTTPException(Exception):
    def __init__(self, status_code, detail=None):
        super().__init__(detail)
        self.status_code, self.detail = status_code, detail


class BaseModel:
    def __init__(self, **kw):
        for k in getattr(type(self), "__annotations__", {}):
            if k in kw:
                setattr(self, k, kw[k])
            elif not hasattr(type(self), k):
                raise TypeError("missing field " + k)

    def dict(self):
        return {k: getattr(self, k) for k in type(self).__annotations__}


class _Resp:
    def __init__(self, content=None, status_code=200, media_type=None, headers=None, **kw):
        self.body, self.status_code, self.media_type, self.headers = content, status_code, media_type, headers or {}


class FastAPI:
    def __init__(self, *a, **k):
        self.routes = {}

    def _reg(self, method):
        def deco(path, **kw):
            def wrap(fn):
                self.routes[(method, path)] = fn
                return fn
            return wrap
        return deco

    def __getattr__(self, name):
        if name in ("get", "post", "put", "patch", "delete"):
            return self._reg(name.upper())
        raise AttributeError(name)

    def mount(self, *a, **k):
        pass

    def middleware(self, kind):
        return lambda fn: fn

    def on_event(self, kind):
        return lambda fn: fn

    def exception_handler(self, exc):
        return lambda fn: fn


def install():
    f = types.ModuleType("fastapi")
    f.FastAPI, f.HTTPException, f.Depends = FastAPI, HTTPException, lambda fn=None: fn
    f.Header = lambda default=None, **k: default
    f.Request = object
    r = types.ModuleType("fastapi.responses")
    r.FileResponse = r.JSONResponse = r.PlainTextResponse = r.Response = _Resp
    st = types.ModuleType("fastapi.staticfiles")
    st.StaticFiles = lambda **k: None
    p = types.ModuleType("pydantic")
    p.BaseModel = BaseModel
    sys.modules.update({"fastapi": f, "fastapi.responses": r, "fastapi.staticfiles": st, "pydantic": p})
