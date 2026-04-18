import http.server
import os


class HelloHandler(http.server.BaseHTTPRequestHandler):
    # The framework instantiates this class once per TCP connection and calls
    # do_GET (or do_POST, etc.) based on the HTTP verb in the request line.
    # You never call do_GET yourself — BaseHTTPRequestHandler dispatches to it.

    def do_GET(self):
        if self.path == "/":
            # Body must be bytes, not str. HTTP is a binary protocol at the
            # transport layer — text has no meaning until the receiver decodes it.
            body = b"Hello, World!\n"
            self.send_response(200)           # writes: HTTP/1.1 200 OK\r\n
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()                # writes the blank line separating headers from body
            self.wfile.write(body)            # wfile wraps the TCP socket's write buffer
        else:
            body = b"Not Found\n"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


if __name__ == "__main__":
    # Read PORT from the environment, fall back to 8080.
    # Set it at runtime: PORT=9090 python3 server.py
    port = int(os.environ.get("PORT", 8080))

    # HTTPServer inherits from socketserver.TCPServer.
    # "0.0.0.0" means: bind to all network interfaces, not just loopback.
    # This is what makes the server reachable from other devices on the LAN.
    # "127.0.0.1" would accept connections from this machine only.
    server = http.server.HTTPServer(("0.0.0.0", port), HelloHandler)
    print(f"Serving on 0.0.0.0:{port}")
    print(f"Local:   http://localhost:{port}/")
    print("LAN:     run `ipconfig getifaddr en0` to get your IP, then open http://<IP>:{port}/".replace("{port}", str(port)))

    try:
        # serve_forever() blocks here, using select() to wait for incoming
        # TCP connections, then hands each one to HelloHandler.
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()  # releases the port immediately (avoids TIME_WAIT)
