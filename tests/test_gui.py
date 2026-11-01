import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from test_fabrizon import demo_jar
from fabrizon.gui import App, make_handler
from http.server import ThreadingHTTPServer


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.app = App()
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **k: None)
        self.port = self.srv.server_address[1]
        self.srv.RequestHandlerClass = make_handler(self.app, self.port)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.port}"

    def tearDown(self):
        self.srv.shutdown(); self.srv.server_close(); self.app.close()

    def req(self, path, data=None, token=True):
        r = urllib.request.Request(self.base + path, data=data, method="POST" if data is not None else "GET")
        if token:
            r.add_header("X-Token", self.app.token)
        try:
            with urllib.request.urlopen(r) as f:
                return f.status, f.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_page_needs_token(self):
        self.assertEqual(self.req("/")[0], 403)
        code, body = self.req("/?t=" + self.app.token)
        self.assertEqual(code, 200)
        self.assertIn(b"Fabrizon", body)

    def test_post_needs_token(self):
        self.assertEqual(self.req("/api/analyze", b"{}", token=False)[0], 403)

    def test_upload_analyze_resolve(self):
        with tempfile.TemporaryDirectory() as t:
            jar = open(demo_jar(t), "rb").read()
        code, b = self.req("/api/upload?kind=jar&name=demo.jar", jar)
        self.assertEqual(code, 200)
        jid = json.loads(b)["id"]
        code, b = self.req("/api/analyze", json.dumps({"id": jid}).encode())
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(b)["mod_id"], "demo")
        code, b = self.req("/api/resolve", json.dumps({"id": jid, "horizon": ""}).encode())
        self.assertEqual(code, 200)
        self.assertIsInstance(json.loads(b), list)
        code, b = self.req("/api/resolve", json.dumps({"id": jid, "horizon": "/no/such/dir"}).encode())
        self.assertEqual(code, 400)

    def test_bad_jar_gives_error_not_crash(self):
        code, b = self.req("/api/upload?kind=jar&name=x.jar", b"not a zip")
        jid = json.loads(b)["id"]
        code, b = self.req("/api/analyze", json.dumps({"id": jid}).encode())
        self.assertEqual(code, 400)
        self.assertIn("error", json.loads(b))


if __name__ == "__main__":
    unittest.main()
