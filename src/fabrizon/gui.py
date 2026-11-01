"""`fabrizon gui`: a local web UI. Standard library only; binds to 127.0.0.1 and needs a random per-run token."""

from __future__ import annotations

import json
import os
import secrets
import shutil
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import io
import zipfile

from .analysis import analyze
from .generate import generate
from .gui_page import PAGE
from .jar import NotAFabricMod, read_jar
from .mappings import MappingError, load_tiny
from .resolve import resolve
from .rustindex import index_tree

MAX_UPLOAD = 512 * 1024 * 1024


class App:
    def __init__(self) -> None:
        self.token = secrets.token_urlsafe(24)
        self.tmp = tempfile.mkdtemp(prefix="fabrizon-")
        self.files: dict[str, str] = {}
        self.lock = threading.Lock()

    def save(self, kind: str, name: str, data: bytes) -> str:
        fid = secrets.token_hex(8)
        ext = ".gz" if name.endswith(".gz") else (".jar" if kind == "jar" else ".tiny")
        path = os.path.join(self.tmp, f"{kind}-{fid}{ext}")
        with open(path, "wb") as f:
            f.write(data)
        with self.lock:
            self.files[fid] = path
        return fid

    def path(self, fid: str | None) -> str:
        with self.lock:
            p = self.files.get(fid or "")
        if not p:
            raise ValueError("unknown file: upload it again")
        return p

    def close(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)


def make_handler(app: App, port: int):
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class H(BaseHTTPRequestHandler):
        server_version = "Fabrizon"

        def log_message(self, *a):  # quiet
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj) -> None:
            self._send(code, json.dumps(obj).encode(), "application/json")

        def _ok_host(self) -> bool:
            return self.headers.get("Host", "") in hosts

        def do_GET(self):
            u = urlparse(self.path)
            if not self._ok_host() or u.path != "/":
                return self._json(404, {"error": "not found"})
            if parse_qs(u.query).get("t", [""])[0] != app.token:
                return self._send(403, b"Open Fabrizon with the link it printed.", "text/plain")
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")

        def do_POST(self):
            u = urlparse(self.path)
            if not self._ok_host() or self.headers.get("X-Token") != app.token:
                return self._json(403, {"error": "forbidden"})
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if n > MAX_UPLOAD:
                    return self._json(413, {"error": "file too large"})
                body = self.rfile.read(n)
                if u.path == "/api/upload":
                    q = parse_qs(u.query)
                    kind = q.get("kind", [""])[0]
                    if kind not in ("jar", "map"):
                        return self._json(400, {"error": "bad kind"})
                    return self._json(200, {"id": app.save(kind, q.get("name", [""])[0], body)})
                req = json.loads(body or b"{}")
                if u.path == "/api/analyze":
                    rep = analyze(read_jar(app.path(req.get("id"))))
                    return self._json(200, rep.to_dict())
                if u.path == "/api/resolve":
                    rep = analyze(read_jar(app.path(req.get("id"))))
                    maps = load_tiny(app.path(req["map_id"])) if req.get("map_id") else None
                    hz = (req.get("horizon") or "").strip().strip('"')
                    if hz and not os.path.isdir(hz):
                        return self._json(400, {"error": f"Horizon folder not found: {hz}"})
                    fns = index_tree(hz) if hz else []
                    rs = resolve(rep, fns, maps, req.get("to") or "named")
                    return self._json(200, [r.to_dict() for r in rs])
                if u.path == "/api/generate":
                    rep = analyze(read_jar(app.path(req.get("id"))))
                    maps = load_tiny(app.path(req["map_id"])) if req.get("map_id") else None
                    hz = (req.get("horizon") or "").strip().strip('"')
                    if not hz or not os.path.isdir(hz):
                        return self._json(400, {"error": "Set a valid Horizon source folder first."})
                    rs = resolve(rep, index_tree(hz), maps, req.get("to") or "named")
                    
                    # Build AI config if provided
                    ai_config = None
                    ai_key = (req.get("ai_key") or "").strip()
                    if ai_key:
                        try:
                            from .ai_translate import AIConfig
                            ai_config = AIConfig(
                                api_key=ai_key,
                                base_url=(req.get("ai_base") or "https://integrate.api.nvidia.com/v1").strip(),
                                model=(req.get("ai_model") or "nvidia/nemotron-3-ultra-550b-a55b").strip(),
                            )
                        except Exception as e:
                            return self._json(400, {"error": f"AI config failed: {e}"})
                    
                    bundle = generate(
                        rep, rs,
                        crate=(req.get("crate") or "horizon_core").strip(),
                        horizon_revision=(req.get("revision") or "").strip() or None,
                        jar=read_jar(app.path(req.get("id"))),
                        ai_config=ai_config,
                    )
                    
                    # If out_dir is provided, write files there too
                    out_dir = (req.get("out") or "").strip()
                    if out_dir:
                        try:
                            from .generate import write_bundle
                            write_bundle(bundle, out_dir)
                        except Exception as e:
                            return self._json(400, {"error": f"Failed to write output folder: {e}"})
                    
                    # If hnmod path provided, package as .hnmod
                    hnmod_path = (req.get("hnmod") or "").strip()
                    if hnmod_path:
                        try:
                            from .package import package_bundle, build_compatibility
                            compat = build_compatibility(
                                hz, game=req.get("game") or "26.3",
                                horizon_revision=(req.get("revision") or "").strip() or None,
                                mixins_revision=(req.get("mixins_revision") or "").strip() or None,
                            )
                            package_bundle(out_dir or tempfile.mkdtemp(prefix="fabrizon_"), hnmod_path, compat)
                        except Exception as e:
                            return self._json(400, {"error": f"Failed to package .hnmod: {e}"})
                    
                    buf = io.BytesIO()
                    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                        for name, text in bundle.files.items():
                            z.writestr(name, text)
                    return self._send(200, buf.getvalue(), "application/zip")
                return self._json(404, {"error": "not found"})
            except (NotAFabricMod, MappingError, ValueError, KeyError, OSError) as e:
                return self._json(400, {"error": str(e)})
            except Exception as e:  # keep the UI alive and tell the user
                return self._json(500, {"error": f"internal error: {type(e).__name__}: {e}"})

    return H


def serve(port: int = 0, open_browser: bool = True) -> int:
    app = App()
    srv = ThreadingHTTPServer(("127.0.0.1", port), lambda *a, **k: None)  # placeholder to learn the port
    real = srv.server_address[1]
    srv.RequestHandlerClass = make_handler(app, real)
    url = f"http://127.0.0.1:{real}/?t={app.token}"
    print(f"Fabrizon is running at {url}\nPress Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        app.close()
    return 0
