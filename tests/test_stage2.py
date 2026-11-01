import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from classbuilder import at, build_class, inject, make_jar, mixin
from fabrizon.analysis import analyze
from fabrizon.cli import main
from fabrizon.jar import read_jar
from fabrizon.mappings import MappingError, parse_tiny
from fabrizon.resolve import parse_selector, resolve, snake
from fabrizon.rustindex import index_source

def _w(p, s):
    with open(p, "w") as f:
        f.write(s)


V1 = "v1\tintermediary\tnamed\nCLASS\tnet/minecraft/class_1234\tnet/minecraft/server/MinecraftServer\n" \
     "METHOD\tnet/minecraft/class_1234\t()V\tmethod_5678\ttickServer\n"
V2 = "tiny\t2\t0\tintermediary\tnamed\nc\tnet/minecraft/class_1234\tnet/minecraft/server/MinecraftServer\n" \
     "\tm\t()V\tmethod_5678\ttickServer\n\t\tp\t1\t\tself\n\tf\tI\tfield_1\tticks\n"

RUST = """
pub mod server {
    pub struct MinecraftServer { ticks: u64 }
    // fn commented_out()
    impl MinecraftServer {
        pub fn tick_server(&mut self) { let s = "fn in_string()"; if true { self.ticks += 1; } }
        fn save(&self) {}
    }
    pub fn helper() {}
}
impl<T> Drop for Wrapper<T> where T: Clone { fn drop(&mut self) {} }
"""


class MappingTests(unittest.TestCase):
    def test_v1_and_v2(self):
        for text in (V1, V2):
            m = parse_tiny(text)
            self.assertEqual(m.map_class("net/minecraft/class_1234", "named"), "net/minecraft/server/MinecraftServer")
            self.assertEqual(m.map_methods("method_5678", "named", owner="net/minecraft/class_1234"), ["tickServer"])
            self.assertEqual(m.map_class("net.minecraft.server.MinecraftServer", "intermediary"), "net/minecraft/class_1234")

    def test_bad_header(self):
        with self.assertRaises(MappingError):
            parse_tiny("nope\n")
        with self.assertRaises(MappingError):
            parse_tiny(V1).map_class("x", "missing")


class RustIndexTests(unittest.TestCase):
    def test_index(self):
        fns = {f.path: f for f in index_source(RUST, "src/lib.rs")}
        self.assertIn("server::MinecraftServer::tick_server", fns)
        self.assertIn("server::helper", fns)
        self.assertNotIn("commented_out", {f.name for f in fns.values()})
        self.assertNotIn("in_string", {f.name for f in fns.values()})
        drop = [f for f in fns.values() if f.name == "drop"][0]
        self.assertEqual((drop.impl_type, drop.trait, drop.module), ("Wrapper", "Drop", ""))

    def test_module_from_file(self):
        f = index_source("fn a() {}", "src/world/chunk.rs")[0]
        self.assertEqual(f.module, "world::chunk")


class ResolveTests(unittest.TestCase):
    def _report(self, tmp, target, method):
        import json, zipfile  # noqa: E401
        P = "com/example/mixin/"
        cls = build_class(P + "M", [mixin(target)], [("h", "()V", 1, [inject(method, at("HEAD"))])])
        path = os.path.join(tmp, "m.jar")
        make_jar(path, {"schemaVersion": 1, "id": "m", "version": "1", "mixins": ["m.mixins.json"]},
                 {"m.mixins.json": {"package": "com.example.mixin", "mixins": ["M"]}}, {P + "M.class": cls})
        return analyze(read_jar(path))

    def test_snake_and_selector(self):
        self.assertEqual(snake("tickServer"), "tick_server")
        s = parse_selector("Lnet/x/Foo;bar(I)V")
        self.assertEqual((s.owner, s.name, s.desc), ("net/x/Foo", "bar", "(I)V"))

    def test_resolves_with_mappings(self):
        with tempfile.TemporaryDirectory() as t:
            rep = self._report(t, "net/minecraft/class_1234", "method_5678")
            fns = index_source(RUST, "src/lib.rs")
            rs = resolve(rep, fns, parse_tiny(V2))
            self.assertEqual(rs[0].status, "resolved")
            self.assertEqual(rs[0].candidates[0].path, "server::MinecraftServer::tick_server")

    def test_needs_mappings_for_intermediary(self):
        with tempfile.TemporaryDirectory() as t:
            rep = self._report(t, "net/minecraft/class_1234", "method_5678")
            self.assertEqual(resolve(rep, index_source(RUST, "src/lib.rs"))[0].status, "needs-mappings")

    def test_named_without_mappings_and_no_match(self):
        with tempfile.TemporaryDirectory() as t:
            fns = index_source(RUST, "src/lib.rs")
            rs = resolve(self._report(t, "net/minecraft/server/MinecraftServer", "tickServer"), fns)
            self.assertEqual(rs[0].status, "resolved")
            rs = resolve(self._report(t, "net/minecraft/server/Nope", "zzz"), fns)
            self.assertEqual(rs[0].status, "unresolved")

    def test_cli(self):
        with tempfile.TemporaryDirectory() as t:
            self._report(t, "net/minecraft/class_1234", "method_5678")
            mp = os.path.join(t, "m.tiny"); _w(mp, V2)
            hz = os.path.join(t, "hz", "src"); os.makedirs(hz)
            _w(os.path.join(hz, "lib.rs"), RUST)
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = main(["resolve", os.path.join(t, "m.jar"), "--mappings", mp, "--horizon", os.path.join(t, "hz")])
            self.assertEqual(rc, 0)
            self.assertIn("server::MinecraftServer::tick_server", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
