"""Recover a mixin handler's body from bytecode (stage 4, piece 1).

This is a small, deliberately conservative decompiler: it rebuilds a readable
statement list from a method's `Code` attribute and translates the parts that are
*mechanically* safe into Rust (primitives, arithmetic, comparisons, string
literals, `if`, locals, returns). Anything that needs knowledge of Horizon's own
API - a call into Minecraft, a field read, an object type - is kept as a comment
and marks the translation incomplete, because guessing a Rust path would only
produce code that fails to compile.

It is not a Java decompiler and never claims to be. Its job is to make the
handler readable and to do the boring part; `translate.py` writes the helper and
the brief, and `horizon-mixins check` is still the only proof.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .classfile import Code, Indy, Insn, Ref, Switch

# JVM descriptor -> Rust type, for the primitives we can name with certainty.
_PRIM: dict[str, str] = {
    "I": "i32", "J": "i64", "F": "f32", "D": "f64", "Z": "bool",
    "B": "i8", "C": "char", "S": "i16", "V": "()",
}

# Java classes with a Rust counterpart that is safe to assume by name alone.
_SAFE_CLASSES = {
    "java/lang/String": "String",
}

CALLBACK = "org/spongepowered/asm/mixin/injection/callback/"
MIXINEXTRAS = "com/llamalad7/mixinextras/"


@dataclass
class Expr:
    text: str
    jty: str          # JVM descriptor when known ("I", "Lfoo/Bar;"), else "?"
    known: bool = True
    ident: str = ""   # when the expression is a plain local/parameter name


@dataclass
class Translation:
    lines: list[str] = field(default_factory=list)
    complete: bool = True
    java_lines: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    used: list[str] = field(default_factory=list)   # local names the body reads

    def note(self, text: str) -> None:
        if text not in self.notes:
            self.notes.append(text)


def type_name(desc: str) -> str:
    """A readable Java type name for a descriptor."""
    if desc in _PRIM:
        return {"I": "int", "J": "long", "F": "float", "D": "double", "Z": "boolean",
                "B": "byte", "C": "char", "S": "short", "V": "void"}[desc]
    if desc.startswith("["):
        return type_name(desc[1:]) + "[]"
    if desc.startswith("L") and desc.endswith(";"):
        return desc[1:-1].replace("/", ".").replace("$", ".")
    return desc


def rust_type(desc: str) -> str | None:
    """The Rust type for a descriptor, when it can be named without Horizon's API."""
    if desc in _PRIM:
        return _PRIM[desc]
    return _SAFE_CLASSES.get(desc[1:-1]) if desc.startswith("L") and desc.endswith(";") else None


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")


_BINOPS = {
    "iadd": "+", "isub": "-", "imul": "*", "idiv": "/", "irem": "%",
    "ladd": "+", "lsub": "-", "lmul": "*", "ldiv": "/", "lrem": "%",
    "fadd": "+", "fsub": "-", "fmul": "*", "fdiv": "/", "frem": "%",
    "dadd": "+", "dsub": "-", "dmul": "*", "dfdiv": "/", "drem": "%",
    "ishl": "<<", "ishr": ">>", "iushr": ">>", "lshl": "<<", "lshr": ">>", "lushr": ">>",
    "iand": "&", "land": "&", "ior": "|", "lor": "|", "ixor": "^", "lxor": "^",
}
_CMP = {
    "if_icmpeq": "==", "if_icmpne": "!=", "if_icmplt": "<", "if_icmpge": ">=",
    "if_icmpgt": ">", "if_icmple": "<=",
}


def _is_callback(desc: str) -> bool:
    return desc.startswith("L" + CALLBACK) or desc.startswith("L" + MIXINEXTRAS)


class Decompiler:
    def __init__(self, code: Code, owner: str, desc: str,
                 renames: dict[int, str] | None = None):
        self.code = code
        self.owner = owner
        self.desc = desc
        self.renames = renames or {}
        self.insns = code.instructions
        self.index = {ins.offset: i for i, ins in enumerate(self.insns)}
        self.locals = {lv.index: lv for lv in code.locals}
        self.stack: list[Expr] = []
        self.out = Translation()
        self.depth = 0
        self.assigned: set[str] = set()
        self.is_static = True

    # -- helpers -------------------------------------------------------
    def local(self, index: int) -> Expr:
        if index in self.renames:
            name = self.renames[index]
            self.out.used.append(name)
            return Expr(name, "?", True, name)
        lv = self.locals.get(index)
        if lv is None:
            return Expr(f"l{index}", "?", False)
        if lv.name == "this":
            return Expr("self", "?", False, "self")
        rt = rust_type(lv.desc)
        e = Expr(lv.name, lv.desc, rt is not None, lv.name)
        self.out.used.append(lv.name)
        return e

    def push(self, e: Expr) -> None:
        self.stack.append(e)

    def pop(self) -> Expr:
        if not self.stack:
            self.out.complete = False
            self.out.note("bytecode stack underflow")
            return Expr("<?>", "?", False)
        return self.stack.pop()

    def emit(self, text: str) -> None:
        self.out.lines.append("    " * (self.depth + 1) + text)

    def java(self, text: str) -> None:
        self.out.java_lines.append("    " * (self.depth + 1) + text)

    def untranslatable(self, java: str, why: str) -> None:
        self.out.complete = False
        self.out.note(why)
        self.emit(f"// TODO(stage 4): {java}")
        self.java(java)

    def render(self, e: Expr) -> str:
        return e.text

    # -- public --------------------------------------------------------
    def run(self) -> Translation:
        self.is_static = self.locals.get(0) is None or self.locals[0].name != "this"
        try:
            self.block(0, len(self.insns))
        except Exception as exc:  # a malformed or exotic method must not crash a bundle
            self.out.complete = False
            self.out.note(f"decompiler stopped: {type(exc).__name__}: {exc}")
        return self.out

    # -- control flow --------------------------------------------------
    def block(self, start: int, end: int) -> None:
        i = start
        while i < end:
            ins = self.insns[i]
            op = ins.op
            if op in _CMP or op in ("ifeq", "ifne", "iflt", "ifge", "ifgt", "ifle",
                                    "ifnull", "ifnonnull", "if_acmpeq", "if_acmpne"):
                i = self.branch(i, end)
                continue
            if op in ("goto", "goto_w"):
                target = self.index.get(ins.arg)
                if target is not None and target > i:
                    i = target  # forward jump with no else: continue at the join
                    continue
                self.untranslatable(f"goto {ins.arg} (loop)", "loops are not translated")
                return
            if op in ("tableswitch", "lookupswitch"):
                self.untranslatable(f"{op} ({len(ins.arg.pairs)} cases)", "switch is not translated")
                return
            if op in ("athrow", "jsr", "jsr_w", "ret"):
                self.untranslatable(op, f"{op} is not translated")
                return
            self.step(ins)
            i += 1

    def branch(self, i: int, end: int) -> int:
        ins = self.insns[i]
        target = self.index.get(ins.arg)
        if target is None or target <= i:
            self.untranslatable(f"{ins.op} {ins.arg} (backward)", "loops are not translated")
            return end
        cond, java_cond = self.condition(ins)
        # if/else when a `goto` right after the then-block jumps past the else block
        then_start, then_end = i + 1, target
        goto_at = then_end - 1
        if goto_at > i and self.insns[goto_at].op in ("goto", "goto_w"):
            join = self.index.get(self.insns[goto_at].arg, end)
            if join > target:
                self.emit(f"if {cond.text if cond else '/* ? */'} {{")
                self.java(f"if ({java_cond}) {{")
                self.depth += 1
                self.block(then_start, goto_at)
                self.depth -= 1
                self.emit("} else {")
                self.java("} else {")
                self.depth += 1
                self.block(target, join)
                self.depth -= 1
                self.emit("}")
                self.java("}")
                if cond is None or not cond.known:
                    self.out.complete = False
                return join
        if cond is None or not cond.known:
            self.out.complete = False
            self.out.note("condition needs Horizon's API")
        self.emit(f"if {cond.text if cond else '/* ? */'} {{")
        self.java(f"if ({java_cond}) {{")
        self.depth += 1
        self.block(then_start, then_end)
        self.depth -= 1
        self.emit("}")
        self.java("}")
        return target

    def condition(self, ins: Insn) -> tuple[Expr | None, str]:
        """Pop the operands and return (Rust condition, Java condition)."""
        op = ins.op
        if op in _CMP:
            b, a = self.pop(), self.pop()
            ok = a.known and b.known and a.jty == b.jty and a.jty in _PRIM
            return Expr(f"{a.text} {_CMP[op]} {b.text}", "Z", ok), f"{a.text} {_CMP[op]} {b.text}"
        if op in ("ifeq", "ifne", "iflt", "ifge", "ifgt", "ifle"):
            a = self.pop()
            if op in ("ifeq", "ifne") and a.jty == "Z":
                return (Expr(a.text, "Z", a.known) if op == "ifne" else Expr(f"!{a.text}", "Z", a.known)), a.text
            cmp = {"ifeq": "==", "ifne": "!=", "iflt": "<", "ifge": ">=", "ifgt": ">", "ifle": "<="}[op]
            ok = a.known and a.jty in _PRIM and a.jty != "Z"
            return Expr(f"{a.text} {cmp} 0", "Z", ok), f"{a.text} {cmp} 0"
        a = self.pop()
        return Expr(f"/* {op} {a.text} */", "Z", False), f"{op}({a.text})"

    # -- straight-line instructions ------------------------------------
    def step(self, ins: Insn) -> None:
        op, arg = ins.op, ins.arg
        if op == "nop":
            return
        if op == "aconst_null":
            self.push(Expr("None", "?", False))
            return
        if op.startswith("iconst_"):
            v = -1 if op == "iconst_m1" else int(op[-1])
            self.push(Expr(str(v), "I"))
            return
        if op.startswith("lconst_"):
            self.push(Expr(op[-1], "J")); return
        if op.startswith("fconst_"):
            self.push(Expr(op[-1] + ".0", "F")); return
        if op.startswith("dconst_"):
            self.push(Expr(op[-1] + ".0", "D")); return
        if op in ("bipush", "sipush"):
            self.push(Expr(str(arg), "I")); return
        if op in ("ldc", "ldc_w", "ldc2_w"):
            kind, value = arg if isinstance(arg, tuple) else ("unknown", arg)
            if kind == "int":
                self.push(Expr(str(value), "I"))
            elif kind == "long":
                self.push(Expr(str(value), "J"))
            elif kind == "float":
                self.push(Expr(repr(value), "F"))
            elif kind == "double":
                self.push(Expr(repr(value), "D"))
            elif kind == "string":
                self.push(Expr(f'"{_escape(str(value))}"', "Ljava/lang/String;"))
            elif kind == "class":
                self.push(Expr(f"/* class {value} */", "?", False))
            else:
                self.push(Expr("/* constant */", "?", False))
            return
        if op in ("iload", "lload", "fload", "dload", "aload"):
            self.push(self.local(arg)); return
        if op.endswith("load_0") or op.endswith("load_1") or op.endswith("load_2") or op.endswith("load_3"):
            self.push(self.local(int(op[-1]))); return
        if op in ("istore", "lstore", "fstore", "dstore", "astore"):
            self.store(self.local(arg).text if arg in self.locals else f"l{arg}", arg)
            return
        if op[-2:] in ("_0", "_1", "_2", "_3") and op[:-2] in ("istore", "lstore", "fstore", "dstore", "astore"):
            self.store(self.local(int(op[-1])).text, int(op[-1]))
            return
        if op == "iinc":
            index, delta = arg
            name = self.locals[index].name if index in self.locals else f"l{index}"
            sign = "+" if delta >= 0 else "-"
            self.emit(f"{name} {sign}= {abs(delta)};")
            self.java(f"{name} {sign}= {abs(delta)};")
            self.out.used.append(name)
            return
        if op in _BINOPS:
            b, a = self.pop(), self.pop()
            known = a.known and b.known and a.jty in _PRIM and b.jty in _PRIM
            self.push(Expr(f"({a.text} {_BINOPS[op]} {b.text})", a.jty if a.jty == b.jty else "?", known))
            return
        if op in ("ineg", "lneg", "fneg", "dneg"):
            a = self.pop()
            self.push(Expr(f"(-{a.text})", a.jty, a.known)); return
        if op in ("i2l", "i2f", "i2d", "l2i", "l2f", "l2d", "f2i", "f2l", "f2d",
                  "d2i", "d2l", "d2f", "i2b", "i2c", "i2s"):
            a = self.pop()
            target = {"i2l": "J", "i2f": "F", "i2d": "D", "l2i": "I", "l2f": "F", "l2d": "D",
                      "f2i": "I", "f2l": "J", "f2d": "D", "d2i": "I", "d2l": "J", "d2f": "F",
                      "i2b": "B", "i2c": "C", "i2s": "S"}[op]
            rt = _PRIM[target]
            self.push(Expr(f"({a.text} as {rt})", target, a.known)); return
        if op in ("pop", "pop2"):
            e = self.pop()
            if e.text and not e.text.startswith("/*"):
                self.emit(f"{e.text};")
                self.java(f"{e.text};")
            return
        if op in ("dup", "dup_x1", "dup_x2", "dup2", "dup2_x1", "dup2_x2", "swap"):
            if op.startswith("dup") and self.stack:
                self.push(self.stack[-1])
            return
        if op in ("getstatic", "getfield"):
            ref: Ref = arg
            if op == "getfield":
                self.pop()
            self.push(Expr(f"/* {ref.owner.rsplit('/', 1)[-1]}.{ref.name} */", ref.desc, False))
            return
        if op in ("putstatic", "putfield"):
            ref: Ref = arg
            value = self.pop()
            if op == "putfield":
                self.pop()
            self.untranslatable(f"{type_name(ref.desc)} {ref.name} = {value.text};",
                                f"field write `{ref.name}` needs Horizon's type")
            return
        if op in ("invokestatic", "invokevirtual", "invokespecial", "invokeinterface"):
            self.invoke(arg, op)
            return
        if op == "invokedynamic":
            self.indynamic(arg)
            return
        if op == "new":
            self.push(Expr(f"/* new {type_name('L' + arg + ';')} */", "?", False))
            return
        if op == "checkcast":
            a = self.pop()
            rt = rust_type("L" + arg + ";") if not arg.startswith("[") else None
            self.push(Expr(a.text, "L" + arg + ";", a.known and rt is not None))
            return
        if op == "instanceof":
            a = self.pop()
            self.push(Expr(f"/* {a.text} instanceof {type_name('L' + arg + ';')} */", "Z", False))
            return
        if op == "arraylength":
            a = self.pop()
            self.push(Expr(f"{a.text}.len()", "I", a.known)); return
        if op in ("iaload", "laload", "faload", "daload", "aaload", "baload", "caload", "saload"):
            idx, arr = self.pop(), self.pop()
            self.push(Expr(f"{arr.text}[{idx.text} as usize]", "?", arr.known and idx.known))
            return
        if op in ("iastore", "lastore", "fastore", "dastore", "aastore", "bastore", "castore", "sastore"):
            value, idx, arr = self.pop(), self.pop(), self.pop()
            self.emit(f"{arr.text}[{idx.text} as usize] = {value.text};")
            self.java(f"{arr.text}[{idx.text}] = {value.text};")
            return
        if op in ("newarray", "anewarray", "multianewarray"):
            n = self.pop()
            self.push(Expr(f"/* new array[{n.text}] */", "?", False))
            return
        if op in ("return", "ireturn", "lreturn", "freturn", "dreturn", "areturn"):
            if op == "return":
                self.emit("")
                self.java("return;")
            else:
                e = self.pop()
                self.emit(f"return {e.text};")
                self.java(f"return {e.text};")
                if not e.known:
                    self.out.complete = False
                    self.out.note("return value needs Horizon's API")
            return
        if op in ("monitorenter", "monitorexit"):
            self.pop(); return
        # anything else: be loud rather than silently wrong
        self.untranslatable(f"// {op} {arg if arg is not None else ''}".strip(), f"opcode {op} is not translated")

    def store(self, name: str, index: int) -> None:
        e = self.pop()
        decl = "let mut " if name not in self.assigned else ""
        if e.known or e.jty in _PRIM:
            self.emit(f"{decl}{name} = {e.text};")
        else:
            self.emit(f"// {decl}{name} = {e.text};")
            self.out.complete = False
        self.java(f"{name} = {e.text};")
        self.assigned.add(name)
        self.out.used.append(name)

    def invoke(self, ref: Ref, op: str) -> None:
        args_desc = [d for d in _split_desc(ref.desc)]
        args = [self.pop() for _ in args_desc][::-1]
        receiver = None
        if op != "invokestatic":
            receiver = self.pop()
        simple = ref.owner.rsplit("/", 1)[-1]

        if ref.owner.startswith(CALLBACK) or ref.owner.startswith(MIXINEXTRAS):
            if ref.name in ("cancel", "setReturnValue", "setReturnValueUnchecked"):
                self.emit("// mixin callback: cancel / set return value (map by hand)")
                self.out.complete = False
                self.out.note("mixin callback needs an explicit contract in the manifest")
                return
        if ref.owner == "java/lang/StringBuilder" and ref.name == "toString":
            self.push(Expr("/* string */", "Ljava/lang/String;", False))
            return
        if ref.owner in ("java/lang/Math", "java/lang/StrictMath"):
            self.push(Expr(f"/* {simple}.{ref.name}(...) */", ref.desc.split(")")[-1] or "V", False))
            return
        if ref.owner.startswith("java/lang/String") and ref.name in ("length", "equals", "isEmpty"):
            arg0 = args[0] if args else None
            if ref.name == "length" and receiver is not None:
                self.push(Expr(f"{receiver.text}.len()", "I", receiver.known)); return
            if ref.name == "isEmpty" and receiver is not None:
                self.push(Expr(f"{receiver.text}.is_empty()", "Z", receiver.known)); return
            if ref.name == "equals" and receiver is not None and arg0 is not None:
                self.push(Expr(f"{receiver.text} == {arg0.text}", "Z",
                               receiver.known and arg0.known)); return

        rendered = ", ".join(a.text for a in args)
        ret_desc = ref.desc.split(")")[-1] or "V"
        call = f"{ref.name}({rendered})"
        if op == "invokestatic":
            shown = f"{simple}.{call}"
        else:
            shown = f"{receiver.text if receiver else '?'}.{call}"
        self.out.complete = False
        self.out.note(f"call `{simple}.{ref.name}` has no known Horizon counterpart")
        self.emit(f"// TODO(stage 4): {shown}  // {type_name(ret_desc)}")
        self.java(f"{shown};")
        if ret_desc != "V":
            self.push(Expr(f"/* {ref.name}(...) */", ret_desc, False))

    def indynamic(self, indy: Indy) -> None:
        # String concatenation is compiled to invokedynamic with makeConcatWithConstants.
        if indy.name.startswith("makeConcat"):
            n = len(_split_desc(indy.desc)) - 1
            parts = [self.pop() for _ in range(n)][::-1]
            known = all(p.known for p in parts)
            text = " + ".join(p.text for p in parts) if parts else '""'
            self.push(Expr(f"format!(\"{{}}\", {text})" if known else "/* string concat */",
                           "Ljava/lang/String;", known))
            return
        n = len(_split_desc(indy.desc)) - 1
        for _ in range(n):
            self.pop()
        self.push(Expr(f"/* invokedynamic {indy.name} */", "?", False))
        self.out.complete = False
        self.out.note(f"invokedynamic `{indy.name}` (lambda) is not translated")


def _split_desc(desc: str) -> list[str]:
    """Parameter descriptors of a JVM method descriptor."""
    if not desc.startswith("("):
        return []
    out, i, n = [], 1, len(desc)
    while i < n and desc[i] != ")":
        j = i
        while j < n and desc[j] == "[":
            j += 1
        if j < n and desc[j] == "L":
            k = desc.find(";", j)
            k = n if k < 0 else k + 1
            out.append(desc[i:k])
            i = k
        else:
            out.append(desc[i : j + 1])
            i = j + 1
    return out


def decompile(code: Code, owner: str, desc: str,
              renames: dict[int, str] | None = None) -> Translation:
    return Decompiler(code, owner, desc, renames).run()
