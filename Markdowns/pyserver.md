# pyserver — Raw Python HTTP Server

**Location:** `src/pyserver/`
**Status:** Complete (barebones v1)
**Dependencies:** None — stdlib only (`http.server`, `os`)

---

## What It Does

Serves a single `GET /` endpoint that returns `Hello, World!` as plain text. Any other path returns a 404. Binds to `0.0.0.0` so it's reachable from any device on the same LAN (e.g. your phone).

---

## Files

| File | Purpose |
|------|---------|
| `server.py` | The HTTP server — request handler class + entry point |
| `__init__.py` | Empty file that marks `pyserver` as a Python package |

---

## Key Concepts

### Why TCP, not UDP?
HTTP requires every byte to arrive in order and intact. TCP's handshake, sequencing, and retransmission guarantee this. UDP makes no delivery guarantees — you'd have to implement reliability yourself. Python's `http.server` is built on `socketserver.TCPServer`, which manages the TCP socket lifecycle.

### `BaseHTTPRequestHandler`
The core abstraction. You subclass it — the framework owns instantiation. For each incoming TCP connection, it:
1. Parses the HTTP request line (e.g. `GET / HTTP/1.1`) and headers
2. Dispatches to a method named `do_<VERB>` — so `GET` → `do_GET`, `POST` → `do_POST`, etc.

You never call `do_GET` yourself; the framework calls it for you.

### HTTP Response Structure (in order)
```
HTTP/1.1 200 OK\r\n          ← send_response(200)
Content-Type: text/plain\r\n  ← send_header(...)
Content-Length: 14\r\n        ← send_header(...)
\r\n                          ← end_headers()  [mandatory blank line]
Hello, World!\n               ← wfile.write(body)
```
The blank line between headers and body is required by the HTTP spec. `end_headers()` writes it.

### Why `bytes`, not `str`?
`wfile` wraps the raw TCP socket write buffer. Sockets transmit bytes — text has no meaning at that layer. The receiver decides how to decode them, guided by the `Content-Type` header. So the body must be `b"Hello, World!\n"`, not `"Hello, World!\n"`.

### `wfile`
A file-like object that wraps the TCP socket's write buffer. Writing to `self.wfile` sends bytes over the wire to the client.

### `0.0.0.0` vs `127.0.0.1`
- `127.0.0.1` — loopback only. Only connections from the same machine are accepted.
- `0.0.0.0` — all interfaces. Connections from any network interface are accepted, including the LAN Wi-Fi interface — this is what allows a phone to connect.

### `PORT` Environment Variable
```python
port = int(os.environ.get("PORT", 8080))
```
`os.environ.get("PORT", 8080)` reads the `PORT` variable from the shell environment, defaulting to `8080`. `int(...)` converts the string value to an integer (required by `HTTPServer`).

Override at runtime:
```bash
PORT=9090 python3 server.py
```

### Graceful Shutdown
```python
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.server_close()
```
`Ctrl-C` raises `KeyboardInterrupt`. `server_close()` closes the listening socket immediately, releasing the port. Without it, the OS keeps the port in `TIME_WAIT` state for ~60 seconds.

### `serve_forever()`
Blocks in an event loop using `select()` to wait for incoming TCP connections. For each connection it:
1. Accepts the TCP handshake
2. Reads the raw HTTP request bytes
3. Instantiates `HelloHandler`
4. Calls the appropriate `do_*` method
5. Loops back to wait for the next connection

---

## How to Run

```bash
cd src/pyserver
python3 server.py
```

Server prints:
```
Serving on 0.0.0.0:8080
Local:   http://localhost:8080/
LAN:     run `ipconfig getifaddr en0` to get your IP, then open http://<IP>:8080/
```

### Access from a Phone
1. Make sure your phone is on the same Wi-Fi as your Mac.
2. Run `ipconfig getifaddr en0` in a terminal — note the IP (e.g. `192.168.1.42`).
3. Open `http://192.168.1.42:8080/` in your phone's browser.
4. If macOS asks to allow incoming connections for Python — click **Allow**.

---

## What's Not Here Yet
- No routing beyond `/`
- No request body parsing
- No static file serving
- No HTTPS
- No logging to a file

These will come in later stages (Flask server, then Node.js).
