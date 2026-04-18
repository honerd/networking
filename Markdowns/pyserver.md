# pyserver — Raw Python HTTP Server

**Location:** `src/pyserver/`
**Status:** v2
**Dependencies:** None — stdlib only (`http.server`, `os`)

---

## What It Does

Two routes, both reachable from any device on the same LAN:

| Route | Response | Content-Type |
|-------|----------|--------------|
| `GET /` | `Hello, World!` | `text/plain` |
| `GET /hello` | Rendered HTML page with an `<h1>` heading | `text/html` |
| Anything else | `Not Found` | `text/plain` (404) |

Binds to `0.0.0.0` so phones on the same Wi-Fi can reach it.

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

## Function Reference

### Functions you defined

#### `do_GET(self)` — `HelloHandler`
```python
def do_GET(self):
```
Called automatically by the framework whenever a `GET` request arrives. You never call this yourself. The dispatch works like this internally:

```python
method = getattr(self, 'do_' + self.command)  # self.command = "GET"
method()                                        # calls do_GET()
```

`self.path` contains the URL path from the request line (e.g. `"/"` or `"/hello"`). The method branches on it to decide what response to send.

---

### Functions/methods you called

#### `os.environ.get(key, default)`
```python
port = int(os.environ.get("PORT", 8080))
```
`os.environ` is a dict-like object mapping environment variable names to their string values. `.get(key, default)` returns the value for `key` if it exists in the environment, or `default` if it doesn't. This is the standard way to make behaviour configurable without hardcoding values.

---

#### `int(x)`
```python
port = int(os.environ.get("PORT", 8080))
```
`int` is a built-in type. Calling it like a function (`int("9090")`) constructs an integer from a string. `HTTPServer` requires an integer port number — environment variables are always strings, so the conversion is mandatory.

---

#### `str(x)`
```python
self.send_header("Content-Length", str(len(body)))
```
`str` is also a built-in type. `str(14)` → `"14"`. HTTP headers are text — the Content-Length value must be a string even though the underlying value is a number.

---

#### `len(x)`
```python
str(len(body))
```
Returns the number of items in a sequence. For a `bytes` object, it returns the byte count. `Content-Length` must be the exact byte count of the body so the client knows when the response ends.

---

#### `http.server.HTTPServer((host, port), HandlerClass)`
```python
server = http.server.HTTPServer(("0.0.0.0", port), HelloHandler)
```
Creates a TCP server socket, binds it to the address and port, and puts it in the listening state. The second argument is the handler class (not an instance) — the server instantiates it fresh for each incoming connection. `HTTPServer` inherits from `socketserver.TCPServer`, which does the actual socket work.

---

#### `server.serve_forever()`
```python
server.serve_forever()
```
Enters a blocking event loop. Internally it calls `select()` (an OS syscall) to wait for activity on the listening socket. When a connection arrives it:
1. Accepts the TCP handshake (completing the 3-way SYN/SYN-ACK/ACK)
2. Reads the raw HTTP request bytes from the socket
3. Instantiates `HelloHandler` and calls the appropriate `do_*` method
4. Loops back to `select()`

It blocks until interrupted (e.g. `KeyboardInterrupt` from Ctrl-C).

---

#### `server.server_close()`
```python
server.server_close()
```
Closes the listening socket. If you skip this after stopping `serve_forever()`, the OS keeps the port in `TIME_WAIT` state for ~60 seconds, which prevents restarting the server immediately on the same port.

---

#### `self.send_response(code)`
```python
self.send_response(200)
```
Writes the HTTP status line to the socket:
```
HTTP/1.1 200 OK\r\n
```
Also adds a `Date` header and `Server` header automatically. Must be called before any `send_header()` calls.

---

#### `self.send_header(name, value)`
```python
self.send_header("Content-Type", "text/plain")
self.send_header("Content-Length", str(len(body)))
```
Writes one header line to the socket:
```
Content-Type: text/plain\r\n
```
Call this once per header. Both arguments must be strings.

---

#### `self.end_headers()`
```python
self.end_headers()
```
Writes the blank line (`\r\n`) that separates the headers section from the body. This is mandated by the HTTP spec — the client uses it to know where headers end and the body begins. Forgetting this call means the client never knows the headers are done and the connection hangs.

---

#### `self.wfile.write(body)`
```python
self.wfile.write(body)
```
`self.wfile` is a file-like object wrapping the write side of the TCP socket. Calling `.write(bytes)` pushes those bytes into the socket's send buffer, which the OS then transmits to the client over the network. The argument must be `bytes`, not `str`.

---

#### `print(...)`
```python
print(f"Serving on 0.0.0.0:{port}")
```
Writes to `stdout` (your terminal). Used here purely for startup information. Python's `print` adds a newline by default (`end="\n"`). f-strings (`f"..."`) embed expressions directly in the string — `{port}` is replaced with the value of the `port` variable at runtime.

---

## What's Not Here Yet
- No request body parsing (POST data)
- No static file serving
- No HTTPS
- No logging to a file

These will come in later stages (Flask server, then Node.js).
