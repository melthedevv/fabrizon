import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from classbuilder import (A, AT, Cls, Enum, MODIFY_ARG, MYSTERY, REDIRECT, SHADOW, WRAP_OP, at, build_class,
                          inject, make_jar, mixin)
from fabrizon.analysis import analyze
from fabrizon.classfile import ClassFormatError, parse_class
from fabrizon.cli import main
from fabrizon.jar import NotAFabricMod, read_jar

SHIFT = "Lorg/spongepowered/asm/mixin/injection/At$Shift;"
MANIFEST = {
    "schemaVersion": 1, "id": "demo", "version": "1.2.3", "license": "MIT", "authors": ["alice"],
    "entrypoints": {"main": ["com.example.Demo"]}, "mixins": ["demo.mixins.json"],
}
CONFIG = {"package": "com.example.mixin", "mixins": ["ServerMixin", "ShadowMixin", "IfaceMixin"],
          "client": ["ClientMixin"]}


def demo_jar(tmp, manifest=MANIFEST, config=CONFIG, extra_classes=None):
    p = os.path.join(tmp, "demo.jar")
    P = "com/example/mixin/"
    classes = {
        P + "ServerMixin.class": build_class(P + "ServerMixin", [mixin("net/minecraft/server/MinecraftServer")], [
            ("onTick", "()V", 1, [inject("tick", at("HEAD"), cancellable=True)]),
            ("onRet", "()V", 1, [inject("save", at("RETURN"))]),
            ("onTail", "()V", 1, [inject("stop", at("TAIL"))]),
            ("afterCall", "()V", 1, [inject("run", at("INVOKE", shift=Enum(SHIFT, "AFTER")))]),
            ("redir", "()V", 1, [A(REDIRECT, {"method": ["x"]})]),
            ("arg", "()V", 1, [A(MODIFY_ARG, {"method": ["y"]})]),
            ("wrap", "()V", 1, [A(WRAP_OP, {"method": ["z"]})]),
            ("weird", "()V", 1, [A(MYSTERY, {"method": ["w"]})]),
        ], refs=["net/fabricmc/fabric/api/event/lifecycle/v1/ServerTickEvents"]),
        P + "ShadowMixin.class": build_class(P + "ShadowMixin", [mixin("net/minecraft/world/level/Level")],
                                             fields=[("seed", "J", 2, [A(SHADOW)])]),
        P + "IfaceMixin.class": build_class(P + "IfaceMixin", [mixin("net/minecraft/world/entity/Entity")],
                                            access=0x0601),
        P + "ClientMixin.class": build_class(P + "ClientMixin", [mixin("net/minecraft/client/Minecraft")], [
            ("onFrame", "()V", 1, [inject("method_1234", at("HEAD"))]),
        ]),
    }
    classes.update(extra_classes or {})
    make_jar(p, manifest, {"demo.mixins.json": config}, classes,
             {"assets/demo/lang/en_us.json": b"{}", "data/demo/recipes/a.json": b"{}", "data/demo/recipes/b.json": b"{}"})
    return p


class ClassFileTests(unittest.TestCase):
    def test_roundtrip_annotations(self):
        data = build_class("a/B", [mixin("x/Y")], [
            ("m", "()V", 1, [inject(["tick"], at("HEAD"), cancellable=True)])], interfaces=["java/lang/Runnable"])
        ci = parse_class(data)
        self.assertEqual(ci.name, "a/B")
        self.assertEqual(ci.interfaces, ["java/lang/Runnable"])
        self.assertEqual(ci.annotations[0].name, "Mixin")
        self.assertEqual(ci.annotations[0].values["value"], ["Lx/Y;"])
        inj = ci.methods[0].annotations[0]
        self.assertEqual(inj.values["method"], ["tick"])
        self.assertIs(inj.values["cancellable"], True)
        self.assertEqual(inj.values["at"][0].values["value"], "HEAD")

    def test_bad_input(self):
        with self.assertRaises(ClassFormatError):
            parse_class(b"nope")
        with self.assertRaises(ClassFormatError):
            parse_class(build_class("a/B")[:20])

    def test_interface_flag(self):
        self.assertTrue(parse_class(build_class("a/I", access=0x0601)).is_interface)


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def report(self, **kw):
        return analyze(read_jar(demo_jar(self.tmp.name, **kw)))

    def find(self, r, member, annotation=None):
        out = [f for f in r.findings if f.member == member and (annotation is None or f.annotation == annotation)]
        self.assertTrue(out, f"no finding for {member}")
        return out[0]

    def test_manifest_and_content(self):
        r = self.report()
        self.assertEqual((r.mod_id, r.version, r.license, r.authors), ("demo", "1.2.3", "MIT", ["alice"]))
        self.assertEqual((r.asset_files, r.data_files), (1, 2))
        self.assertEqual(r.entrypoints, {"main": ["com.example.Demo"]})

    def test_kinds(self):
        r = self.report()
        head = self.find(r, "onTick")
        self.assertEqual((head.horizon, head.status), ("HEAD", "mappable"))
        self.assertIn("cancellable", head.note)
        self.assertEqual(self.find(r, "onRet").horizon, "RETURN")
        self.assertEqual(self.find(r, "afterCall").horizon, "AFTER_CALL")
        self.assertEqual(self.find(r, "arg").horizon, "MODIFY_ARG")
        self.assertEqual(self.find(r, "wrap").horizon, "WRAP_OPERATION")
        self.assertEqual(head.targets, ["net/minecraft/server/MinecraftServer"])
        self.assertEqual(head.selectors, ["tick"])

    def test_blocked(self):
        r = self.report()
        for member in ("onTail", "redir", "weird", "seed", "(class)"):
            self.assertEqual(self.find(r, member).status, "blocked", member)

    def test_sides(self):
        r = self.report()
        self.assertEqual(r.sides, {"common": 3, "client": 1, "server": 0})
        self.assertEqual(self.find(r, "onFrame").side, "client")

    def test_environment_overrides_side(self):
        m = {**MANIFEST, "mixins": [{"config": "demo.mixins.json", "environment": "server"}]}
        self.assertEqual(self.report(manifest=m).sides["server"], 4)

    def test_fabric_api_and_intermediary(self):
        r = self.report()
        self.assertEqual(r.fabric_api_refs, ["net/fabricmc/fabric/api/event/lifecycle/v1/ServerTickEvents"])
        self.assertTrue(r.intermediary_names)  # method_1234 in ClientMixin

    def test_counts(self):
        c = self.report().counts()
        self.assertEqual(sum(c.values()), len(self.report().findings))
        self.assertGreater(c["blocked"], 0)

    def test_missing_mixin_class_warns(self):
        cfg = {**CONFIG, "mixins": CONFIG["mixins"] + ["Ghost"]}
        self.assertTrue(any("Ghost" in w for w in self.report(config=cfg).warnings))

    def test_corrupt_class_warns_not_crashes(self):
        r = self.report(extra_classes={"com/example/Broken.class": b"\xca\xfe\xba\xbe\x00"})
        self.assertTrue(any("Broken" in w for w in r.warnings))


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_text_and_json(self):
        with tempfile.TemporaryDirectory() as t:
            jar = demo_jar(t)
            code, out, _ = self.run_cli("analyze", jar)
            self.assertEqual(code, 0)
            self.assertIn("feasibility report: demo 1.2.3", out)
            self.assertIn("BLOCKED", out)
            code, out, _ = self.run_cli("analyze", jar, "--json")
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["mod_id"], "demo")

    def test_not_a_fabric_mod(self):
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, "x.jar")
            make_jar(p, None)
            code, _, err = self.run_cli("analyze", p)
            self.assertEqual(code, 2)
            self.assertIn("fabric.mod.json", err)
            with self.assertRaises(NotAFabricMod):
                read_jar(os.path.join(t, "missing.jar"))


if __name__ == "__main__":
    unittest.main()
