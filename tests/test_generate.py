import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from classbuilder import at, build_class, inject, make_jar, mixin
from fabrizon.analysis import analyze
from fabrizon.generate import generate, target_id
from fabrizon.jar import read_jar
from fabrizon.resolve import resolve
from fabrizon.rustindex import index_source

RUST = "pub mod server { pub struct MinecraftServer; impl MinecraftServer { pub fn tick_server(&mut self) {} pub fn save(&self) {} } }"


class GenerateTests(unittest.TestCase):
    def _bundle(self, t, rev=None):
        P = "com/example/mixin/"
        cls = build_class(P + "M", [mixin("net/minecraft/server/MinecraftServer")], [
            ("a", "()V", 1, [inject("tickServer", at("HEAD"))]),
            ("b", "()V", 1, [inject("save", at("RETURN"))]),
            ("c", "()V", 1, [inject("nothingHere", at("HEAD"))]),
        ])
        p = os.path.join(t, "m.jar")
        make_jar(p, {"schemaVersion": 1, "id": "My Mod!", "version": "2.0", "license": "MIT", "authors": ["alice"],
                     "mixins": ["m.mixins.json"]},
                 {"m.mixins.json": {"package": "com.example.mixin", "mixins": ["M"]}}, {P + "M.class": cls})
        rep = analyze(read_jar(p))
        return generate(rep, resolve(rep, index_source(RUST, "src/lib.rs")), "horizon-core", rev)

    def test_head_and_return_emitted_others_todo(self):
        with tempfile.TemporaryDirectory() as t:
            b = self._bundle(t, "a" * 40)
        toml = b.files["horizon-mixin.toml"]
        self.assertIn('id = "my_mod"', toml)
        self.assertIn('target = "horizon_core::server::MinecraftServer::tick_server"', toml)
        self.assertIn('target = "horizon_core::server::MinecraftServer::save"', toml)
        self.assertIn('kind = "HEAD"', toml)
        self.assertIn('kind = "RETURN"', toml)
        self.assertIn("bindings = []", toml)
        self.assertIn('horizon_revision = "' + "a" * 40 + '"', toml)
        self.assertEqual(toml.count("[[injection]]"), 2)
        # the unresolved handler still needs a human
        self.assertIn("unresolved", b.files["TODO.md"])
        self.assertIn("alice", b.files["NOTICE.md"])
        self.assertIn("BRIEF.md", b.files)
        helper = [k for k in b.files if k.endswith(".rs")]
        self.assertEqual(len(helper), 2)
        self.assertIn("fn ", b.files[helper[0]])

    def test_toml_parses(self):
        try:
            import tomllib
        except ImportError:
            self.skipTest("tomllib needs Python 3.11+")
        with tempfile.TemporaryDirectory() as t:
            b = self._bundle(t)
        d = tomllib.loads(b.files["horizon-mixin.toml"])
        self.assertEqual(d["mod"]["version"], "2.0")
        self.assertEqual(d["injection"][0]["bindings"], [])

    def test_bad_revision(self):
        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as t:
                self._bundle(t, "abc")

    def test_target_id(self):
        self.assertEqual(target_id("horizon-core", "a::B::c"), "horizon_core::a::B::c")


if __name__ == "__main__":
    unittest.main()
