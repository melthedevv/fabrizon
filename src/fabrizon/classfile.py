"""A minimal Java class-file reader.

Reads what Fabrizon needs to recover Mixin annotations and handler bodies: the
constant pool, class/field/method annotations, the set of classes the file
refers to, and each method's bytecode (`Code` attribute) with its constant-pool
references resolved. Pure standard library; no bytecode is executed, and nothing
is decompiled to Java source here (stage 4 does that, in `javacode.py`).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

ACC_INTERFACE = 0x0200
_ANNOTATION_ATTRS = {"RuntimeVisibleAnnotations", "RuntimeInvisibleAnnotations"}

# Constant-pool tags.
_UTF8, _INT, _FLOAT, _LONG, _DOUBLE = 1, 3, 4, 5, 6
_CLASS, _STRING, _FIELDREF, _METHODREF, _IMETHODREF = 7, 8, 9, 10, 11
_NAMEANDTYPE, _METHODHANDLE, _METHODTYPE, _DYNAMIC, _INVOKEDYNAMIC = 12, 15, 16, 17, 18
_MODULE, _PACKAGE = 19, 20


class ClassFormatError(ValueError):
    """The bytes are not a class file this reader understands."""


@dataclass
class Annotation:
    type: str  # field descriptor, e.g. "Lorg/spongepowered/asm/mixin/injection/Inject;"
    values: dict[str, Any] = field(default_factory=dict)

    @property
    def internal_name(self) -> str:
        t = self.type
        return t[1:-1] if t.startswith("L") and t.endswith(";") else t

    @property
    def name(self) -> str:
        return self.internal_name.rsplit("/", 1)[-1]


@dataclass(frozen=True)
class Ref:
    """A resolved field/method reference from the constant pool."""

    kind: str  # "field" | "method" | "interface"
    owner: str  # internal class name, e.g. "java/lang/Math"
    name: str
    desc: str


@dataclass(frozen=True)
class Indy:
    """An `invokedynamic` instruction (string concatenation, lambdas)."""

    name: str
    desc: str
    bootstrap: int
    args: tuple[Any, ...] = ()


@dataclass(frozen=True)
class Switch:
    default: int
    pairs: tuple[tuple[int, int], ...]


@dataclass
class Insn:
    offset: int
    op: str
    arg: Any = None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"{self.offset}:{self.op}" + (f" {self.arg}" if self.arg is not None else "")


@dataclass
class LocalVar:
    index: int
    name: str
    desc: str
    start: int
    length: int


@dataclass
class Code:
    max_stack: int
    max_locals: int
    instructions: list[Insn] = field(default_factory=list)
    locals: list[LocalVar] = field(default_factory=list)


@dataclass
class Member:
    name: str
    descriptor: str
    access: int
    annotations: list[Annotation] = field(default_factory=list)
    code: Code | None = None
    signature: str | None = None  # the generic `Signature` attribute, when present

    @property
    def is_static(self) -> bool:
        return bool(self.access & 0x0008)

    @property
    def is_public(self) -> bool:
        return bool(self.access & 0x0001)


@dataclass
class ClassInfo:
    name: str
    super_name: str | None
    interfaces: list[str]
    access: int
    annotations: list[Annotation]
    fields: list[Member]
    methods: list[Member]
    class_refs: list[str]
    utf8: list[str]
    major: int = 0

    @property
    def is_interface(self) -> bool:
        return bool(self.access & ACC_INTERFACE)

    def method(self, name: str, desc: str | None = None) -> Member | None:
        for m in self.methods:
            if m.name == name and (desc is None or m.descriptor == desc):
                return m
        return None


class _Buf:
    def __init__(self, data: bytes):
        self.d = data
        self.i = 0

    def raw(self, n: int) -> bytes:
        if self.i + n > len(self.d):
            raise ClassFormatError("truncated class file")
        b = self.d[self.i : self.i + n]
        self.i += n
        return b

    def u1(self) -> int:
        return self.raw(1)[0]

    def u2(self) -> int:
        return struct.unpack(">H", self.raw(2))[0]

    def u4(self) -> int:
        return struct.unpack(">I", self.raw(4))[0]

    def s1(self) -> int:
        return struct.unpack(">b", self.raw(1))[0]

    def s2(self) -> int:
        return struct.unpack(">h", self.raw(2))[0]

    def s4(self) -> int:
        return struct.unpack(">i", self.raw(4))[0]


# opcode -> (mnemonic, operand kind)
# kinds: "" none, "u1", "s1", "u2", "s2", "branch", "cp1", "cp2", "field", "method",
#        "class", "iinc", "newarray", "switch", "invokeinterface", "invokedynamic",
#        "multianewarray", "wide", "branch4", "invokeinterface"
_OPS: dict[int, tuple[str, str]] = {}


def _def(start: int, names: str, kind: str = "") -> None:
    for i, name in enumerate(names.split()):
        _OPS[start + i] = (name, kind)


_def(0x00, "nop")
_def(0x01, "aconst_null")
_def(0x02, "iconst_m1 iconst_0 iconst_1 iconst_2 iconst_3 iconst_4 iconst_5")
_def(0x09, "lconst_0 lconst_1")
_def(0x0b, "fconst_0 fconst_1 fconst_2")
_def(0x0e, "dconst_0 dconst_1")
_def(0x10, "bipush", "s1")
_def(0x11, "sipush", "s2")
_def(0x12, "ldc", "cp1")
_def(0x13, "ldc_w", "cp2")
_def(0x14, "ldc2_w", "cp2")
_def(0x15, "iload lload fload dload aload", "u1")
_def(0x1a, "iload_0 iload_1 iload_2 iload_3")
_def(0x1e, "lload_0 lload_1 lload_2 lload_3")
_def(0x22, "fload_0 fload_1 fload_2 fload_3")
_def(0x26, "dload_0 dload_1 dload_2 dload_3")
_def(0x2a, "aload_0 aload_1 aload_2 aload_3")
_def(0x2e, "iaload laload faload daload aaload baload caload saload")
_def(0x36, "istore lstore fstore dstore astore", "u1")
_def(0x3b, "istore_0 istore_1 istore_2 istore_3")
_def(0x3f, "lstore_0 lstore_1 lstore_2 lstore_3")
_def(0x43, "fstore_0 fstore_1 fstore_2 fstore_3")
_def(0x47, "dstore_0 dstore_1 dstore_2 dstore_3")
_def(0x4b, "astore_0 astore_1 astore_2 astore_3")
_def(0x4f, "iastore lastore fastore dastore aastore bastore castore sastore")
_def(0x57, "pop pop2 dup dup_x1 dup_x2 dup2 dup2_x1 dup2_x2 swap")
_def(0x60, "iadd ladd fadd dadd isub lsub fsub dsub imul lmul fmul dmul "
           "idiv ldiv fdiv ddiv irem lrem frem drem ineg lneg fneg dneg "
           "ishl lshl ishr lshr iushr lushr iand land ior lor ixor lxor")
_def(0x84, "iinc", "iinc")
_def(0x85, "i2l i2f i2d l2i l2f l2d f2i f2l f2d d2i d2l d2f i2b i2c i2s")
_def(0x94, "lcmp fcmpl fcmpg dcmpl dcmpg")
_def(0x99, "ifeq ifne iflt ifge ifgt ifle if_icmpeq if_icmpne if_icmplt "
           "if_icmpge if_icmpgt if_icmple if_acmpeq if_acmpne goto jsr", "branch")
_def(0xa9, "ret", "u1")
_def(0xaa, "tableswitch lookupswitch", "switch")
_def(0xac, "ireturn lreturn freturn dreturn areturn return")
_def(0xb2, "getstatic putstatic getfield putfield", "field")
_def(0xb6, "invokevirtual invokespecial invokestatic", "method")
_def(0xb9, "invokeinterface", "invokeinterface")
_def(0xba, "invokedynamic", "invokedynamic")
_def(0xbb, "new", "class")
_def(0xbc, "newarray", "newarray")
_def(0xbd, "anewarray", "class")
_def(0xbe, "arraylength athrow")
_def(0xc0, "checkcast instanceof", "class")
_def(0xc2, "monitorenter monitorexit")
_def(0xc4, "wide", "wide")
_def(0xc5, "multianewarray", "multianewarray")
_def(0xc6, "ifnull ifnonnull", "branch")
_def(0xc8, "goto_w jsr_w", "branch4")

_ATYPE = {4: "Z", 5: "C", 6: "F", 7: "D", 8: "B", 9: "S", 10: "I", 11: "J"}


def _decode(pool: list[tuple | None], entry, utf) -> tuple[str, int]:
    """Decode a loadable constant at `idx` -> (kind, value)."""
    tag = entry[0]
    if tag == _INT:
        return "int", entry[1]
    if tag == _FLOAT:
        return "float", entry[1]
    if tag == _LONG:
        return "long", entry[1]
    if tag == _DOUBLE:
        return "double", entry[1]
    if tag == _STRING:
        return "string", utf(entry[1])
    if tag == _CLASS:
        return "class", utf(entry[1])
    if tag == _METHODHANDLE:
        return "handle", entry
    if tag == _METHODTYPE:
        return "methodtype", utf(entry[1])
    if tag == _DYNAMIC:
        return "dynamic", entry
    return "unknown", entry


def parse_class(data: bytes) -> ClassInfo:
    b = _Buf(data)
    if b.u4() != 0xCAFEBABE:
        raise ClassFormatError("bad magic number")
    b.u2()  # minor
    major = b.u2()
    count = b.u2()
    pool: list[tuple | None] = [None] * count
    i = 1
    while i < count:
        tag = b.u1()
        if tag == _UTF8:
            pool[i] = (_UTF8, b.raw(b.u2()).decode("utf-8", "replace"))
        elif tag == _INT:
            pool[i] = (_INT, struct.unpack(">i", b.raw(4))[0])
        elif tag == _FLOAT:
            pool[i] = (_FLOAT, struct.unpack(">f", b.raw(4))[0])
        elif tag == _LONG:
            pool[i] = (_LONG, struct.unpack(">q", b.raw(8))[0])
            i += 1
        elif tag == _DOUBLE:
            pool[i] = (_DOUBLE, struct.unpack(">d", b.raw(8))[0])
            i += 1
        elif tag in (_CLASS, _STRING, _METHODTYPE, _MODULE, _PACKAGE):
            pool[i] = (tag, b.u2())
        elif tag in (_FIELDREF, _METHODREF, _IMETHODREF, _NAMEANDTYPE, _DYNAMIC, _INVOKEDYNAMIC):
            pool[i] = (tag, b.u2(), b.u2())
        elif tag == _METHODHANDLE:
            pool[i] = (tag, b.u1(), b.u2())
        else:
            raise ClassFormatError(f"unknown constant-pool tag {tag}")
        i += 1

    def entry(idx: int) -> tuple:
        if not 0 < idx < count or pool[idx] is None:
            raise ClassFormatError(f"bad constant-pool index {idx}")
        return pool[idx]  # type: ignore[return-value]

    def utf(idx: int) -> str:
        e = entry(idx)
        if e[0] != _UTF8:
            raise ClassFormatError("expected a UTF-8 constant")
        return e[1]

    def cls(idx: int) -> str:
        e = entry(idx)
        if e[0] != _CLASS:
            raise ClassFormatError("expected a class constant")
        return utf(e[1])

    def name_and_type(idx: int) -> tuple[str, str]:
        e = entry(idx)
        if e[0] != _NAMEANDTYPE:
            raise ClassFormatError("expected a NameAndType constant")
        return utf(e[1]), utf(e[2])

    def member_ref(idx: int) -> Ref:
        e = entry(idx)
        if e[0] not in (_FIELDREF, _METHODREF, _IMETHODREF):
            raise ClassFormatError("expected a member reference")
        owner = cls(e[1])
        name, desc = name_and_type(e[2])
        kind = {_FIELDREF: "field", _METHODREF: "method", _IMETHODREF: "interface"}[e[0]]
        return Ref(kind, owner, name, desc)

    def element(buf: _Buf) -> Any:
        tag = chr(buf.u1())
        if tag in "BCDFIJSZ":
            v = entry(buf.u2())[1]
            return bool(v) if tag == "Z" else v
        if tag == "s":
            return utf(buf.u2())
        if tag == "e":
            buf.u2()  # enum type descriptor
            return utf(buf.u2())  # constant name, e.g. "HEAD"
        if tag == "c":
            return utf(buf.u2())
        if tag == "@":
            return annotation(buf)
        if tag == "[":
            return [element(buf) for _ in range(buf.u2())]
        raise ClassFormatError(f"unknown element-value tag {tag!r}")

    def annotation(buf: _Buf) -> Annotation:
        ann = Annotation(utf(buf.u2()))
        for _ in range(buf.u2()):
            key = utf(buf.u2())
            ann.values[key] = element(buf)
        return ann

    bootstraps: list[tuple[int, list[int]]] = []

    def read_code(buf: _Buf) -> Code:
        max_stack, max_locals, code_len = buf.u2(), buf.u2(), buf.u4()
        code = Code(max_stack, max_locals)
        raw = buf.raw(code_len)
        pos = 0
        while pos < code_len:
            offset = pos
            opcode = raw[pos]
            pos += 1
            spec = _OPS.get(opcode)
            if spec is None:
                raise ClassFormatError(f"unknown opcode 0x{opcode:02x} at {offset}")
            mnemonic, kind = spec
            arg: Any = None
            if kind == "":
                pass
            elif kind == "u1":
                arg = raw[pos]
                pos += 1
            elif kind == "s1":
                arg = struct.unpack(">b", raw[pos : pos + 1])[0]
                pos += 1
            elif kind == "u2":
                arg = struct.unpack(">H", raw[pos : pos + 2])[0]
                pos += 2
            elif kind == "s2":
                arg = struct.unpack(">h", raw[pos : pos + 2])[0]
                pos += 2
            elif kind == "branch":
                arg = offset + struct.unpack(">h", raw[pos : pos + 2])[0]
                pos += 2
            elif kind == "branch4":
                arg = offset + struct.unpack(">i", raw[pos : pos + 4])[0]
                pos += 4
            elif kind in ("cp1", "cp2"):
                idx = raw[pos] if kind == "cp1" else struct.unpack(">H", raw[pos : pos + 2])[0]
                pos += 1 if kind == "cp1" else 2
                arg = _decode(pool, entry(idx), utf)
            elif kind in ("field", "method", "class"):
                idx = struct.unpack(">H", raw[pos : pos + 2])[0]
                pos += 2
                arg = cls(idx) if kind == "class" else member_ref(idx)
            elif kind == "iinc":
                arg = (raw[pos], struct.unpack(">b", raw[pos + 1 : pos + 2])[0])
                pos += 2
            elif kind == "newarray":
                arg = _ATYPE.get(raw[pos], "?")
                pos += 1
            elif kind == "invokeinterface":
                idx = struct.unpack(">H", raw[pos : pos + 2])[0]
                pos += 4  # index, count, 0
                arg = member_ref(idx)
            elif kind == "invokedynamic":
                idx = struct.unpack(">H", raw[pos : pos + 2])[0]
                pos += 4  # index, 0, 0
                e = entry(idx)
                if e[0] != _INVOKEDYNAMIC:
                    raise ClassFormatError("expected an InvokeDynamic constant")
                name, desc = name_and_type(e[2])
                boot_index = e[1]
                bargs: tuple[Any, ...] = ()
                if boot_index < len(bootstraps):
                    bargs = tuple(bootstraps[boot_index][1])
                arg = Indy(name, desc, boot_index, bargs)
            elif kind == "multianewarray":
                idx = struct.unpack(">H", raw[pos : pos + 2])[0]
                dims = raw[pos + 2]
                pos += 3
                arg = (cls(idx), dims)
            elif kind == "switch":
                while pos % 4:
                    pos += 1
                default = offset + struct.unpack(">i", raw[pos : pos + 4])[0]
                pos += 4
                if mnemonic == "tableswitch":
                    low, high = struct.unpack(">ii", raw[pos : pos + 8])
                    pos += 8
                    pairs = tuple(
                        (low + k, offset + struct.unpack(">i", raw[pos + 4 * k : pos + 4 * k + 4])[0])
                        for k in range(high - low + 1)
                    )
                    pos += 4 * len(pairs)
                else:
                    n = struct.unpack(">i", raw[pos : pos + 4])[0]
                    pos += 4
                    pairs = tuple(
                        (struct.unpack(">i", raw[pos + 8 * k : pos + 8 * k + 4])[0],
                         offset + struct.unpack(">i", raw[pos + 8 * k + 4 : pos + 8 * k + 8])[0])
                        for k in range(n)
                    )
                    pos += 8 * len(pairs)
                arg = Switch(default, pairs)
            elif kind == "wide":
                opcode2 = raw[pos]
                pos += 1
                spec2 = _OPS.get(opcode2)
                if spec2 is None:
                    raise ClassFormatError("bad wide opcode")
                if spec2[0] == "iinc":
                    arg = (struct.unpack(">H", raw[pos : pos + 2])[0],
                           struct.unpack(">h", raw[pos + 2 : pos + 4])[0])
                    pos += 4
                else:
                    arg = struct.unpack(">H", raw[pos : pos + 2])[0]
                    pos += 2
                mnemonic = spec2[0]
            code.instructions.append(Insn(offset, mnemonic, arg))
        for _ in range(buf.u2()):  # exception table
            buf.u2(); buf.u2(); buf.u2(); buf.u2()
        for _ in range(buf.u2()):  # Code sub-attributes
            sub_name = utf(buf.u2())
            sub_len = buf.u4()
            if sub_name == "LocalVariableTable":
                sub = _Buf(buf.raw(sub_len))
                for _ in range(sub.u2()):
                    start, length = sub.u2(), sub.u2()
                    name_idx, desc_idx, index = sub.u2(), sub.u2(), sub.u2()
                    code.locals.append(LocalVar(index, utf(name_idx), utf(desc_idx), start, length))
            else:
                buf.raw(sub_len)
        return code

    def attributes(buf: _Buf) -> list[Annotation]:
        found: list[Annotation] = []
        for _ in range(buf.u2()):
            name = utf(buf.u2())
            length = buf.u4()
            if name in _ANNOTATION_ATTRS:
                sub = _Buf(buf.raw(length))
                found.extend(annotation(sub) for _ in range(sub.u2()))
            elif name == "BootstrapMethods":
                sub = _Buf(buf.raw(length))
                for _ in range(sub.u2()):
                    method_ref = sub.u2()
                    bootstraps.append((method_ref, [sub.u2() for _ in range(sub.u2())]))
            else:
                buf.raw(length)
        return found

    pending_code: list[tuple[Member, bytes]] = []

    def member_attributes(buf: _Buf, member: Member) -> None:
        for _ in range(buf.u2()):
            name = utf(buf.u2())
            length = buf.u4()
            if name in _ANNOTATION_ATTRS:
                sub = _Buf(buf.raw(length))
                member.annotations.extend(annotation(sub) for _ in range(sub.u2()))
            elif name == "Code":
                # BootstrapMethods is a class attribute that comes after the methods,
                # so bytecode is decoded once the whole file has been read.
                pending_code.append((member, buf.raw(length)))
            elif name == "Signature":
                sub = _Buf(buf.raw(length))
                member.signature = utf(sub.u2())
            else:
                buf.raw(length)

    def members(buf: _Buf) -> list[Member]:
        out = []
        for _ in range(buf.u2()):
            access = buf.u2()
            name = utf(buf.u2())
            desc = utf(buf.u2())
            m = Member(name, desc, access)
            member_attributes(buf, m)
            out.append(m)
        return out

    access = b.u2()
    this_name = cls(b.u2())
    super_idx = b.u2()
    super_name = cls(super_idx) if super_idx else None
    interfaces = [cls(b.u2()) for _ in range(b.u2())]
    fields_ = members(b)
    methods = members(b)
    annotations = attributes(b)
    for _member, _raw in pending_code:
        _member.code = read_code(_Buf(_raw))

    refs = sorted(
        {
            utf(e[1])
            for e in pool
            if e and e[0] == _CLASS and not utf(e[1]).startswith("[")
        }
    )
    strings = [e[1] for e in pool if e and e[0] == _UTF8]
    return ClassInfo(
        this_name, super_name, interfaces, access, annotations, fields_, methods, refs, strings, major
    )
