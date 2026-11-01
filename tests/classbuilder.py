"""Assemble tiny but valid .class files (with annotations) and mod jars for tests."""

from __future__ import annotations

import io
import json
import struct
import zipfile
from dataclasses import dataclass, field
from typing import Any

MIXIN = "Lorg/spongepowered/asm/mixin/Mixin;"
INJECT = "Lorg/spongepowered/asm/mixin/injection/Inject;"
AT = "Lorg/spongepowered/asm/mixin/injection/At;"
REDIRECT = "Lorg/spongepowered/asm/mixin/injection/Redirect;"
MODIFY_ARG = "Lorg/spongepowered/asm/mixin/injection/ModifyArg;"
SHADOW = "Lorg/spongepowered/asm/mixin/Shadow;"
WRAP_OP = "Lcom/llamalad7/mixinextras/injector/wrapoperation/WrapOperation;"
MYSTERY = "Lcom/llamalad7/mixinextras/injector/WrapWithCondition;"


@dataclass
class A:
    type: str
    values: dict[str, Any] = field(default_factory=dict)


@dataclass
class Enum:
    type: str
    name: str


@dataclass
class Cls:
    desc: str


class _Pool:
    def __init__(self):
        self.items: list[bytes] = []
        self.map: dict[tuple, int] = {}

    def _add(self, key, raw):
        if key not in self.map:
            self.items.append(raw)
            self.map[key] = len(self.items)
        return self.map[key]

    def utf8(self, s: str) -> int:
        b = s.encode()
        return self._add(("u", s), b"\x01" + struct.pack(">H", len(b)) + b)

    def klass(self, n: str) -> int:
        return self._add(("c", n), b"\x07" + struct.pack(">H", self.utf8(n)))

    def integer(self, v: int) -> int:
        return self._add(("i", v), b"\x03" + struct.pack(">i", v))


def _u2(v: int) -> bytes:
    return struct.pack(">H", v)


def _val(p: _Pool, v) -> bytes:
    if isinstance(v, bool):
        return b"Z" + _u2(p.integer(int(v)))
    if isinstance(v, int):
        return b"I" + _u2(p.integer(v))
    if isinstance(v, str):
        return b"s" + _u2(p.utf8(v))
    if isinstance(v, Enum):
        return b"e" + _u2(p.utf8(v.type)) + _u2(p.utf8(v.name))
    if isinstance(v, Cls):
        return b"c" + _u2(p.utf8(v.desc))
    if isinstance(v, A):
        return b"@" + _ann(p, v)
    if isinstance(v, list):
        return b"[" + _u2(len(v)) + b"".join(_val(p, x) for x in v)
    raise TypeError(v)


def _ann(p: _Pool, a: A) -> bytes:
    out = _u2(p.utf8(a.type)) + _u2(len(a.values))
    for k, v in a.values.items():
        out += _u2(p.utf8(k)) + _val(p, v)
    return out


def _attrs(p: _Pool, anns: list[A]) -> bytes:
    if not anns:
        return _u2(0)
    body = _u2(len(anns)) + b"".join(_ann(p, a) for a in anns)
    return _u2(1) + _u2(p.utf8("RuntimeInvisibleAnnotations")) + struct.pack(">I", len(body)) + body


def build_class(name, anns=(), methods=(), fields=(), access=0x21, super_name="java/lang/Object",
                interfaces=(), refs=()) -> bytes:
    p = _Pool()
    this_i, super_i = p.klass(name), p.klass(super_name)
    iface = [p.klass(i) for i in interfaces]
    for r in refs:
        p.klass(r)

    def members(items):
        out = _u2(len(items))
        for n, d, acc, a in items:
            out += _u2(acc) + _u2(p.utf8(n)) + _u2(p.utf8(d)) + _attrs(p, a)
        return out

    body = _u2(access) + _u2(this_i) + _u2(super_i) + _u2(len(iface)) + b"".join(_u2(i) for i in iface)
    body += members(list(fields)) + members(list(methods)) + _attrs(p, list(anns))
    return b"\xca\xfe\xba\xbe" + _u2(0) + _u2(52) + _u2(len(p.items) + 1) + b"".join(p.items) + body


def at(value: str, **kw) -> A:
    return A(AT, {"value": value, **kw})


def inject(method, *ats, **kw) -> A:
    return A(INJECT, {"method": method if isinstance(method, list) else [method], "at": list(ats), **kw})


def mixin(*targets: str) -> A:
    return A(MIXIN, {"value": [Cls(f"L{t};") for t in targets]})


def make_jar(path, manifest, configs=None, classes=None, extra=None):
    with zipfile.ZipFile(path, "w") as z:
        if manifest is not None:
            z.writestr("fabric.mod.json", json.dumps(manifest))
        for n, c in (configs or {}).items():
            z.writestr(n, json.dumps(c))
        for n, b in (classes or {}).items():
            z.writestr(n, b)
        for n, b in (extra or {}).items():
            z.writestr(n, b)
