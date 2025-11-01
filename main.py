import http.server
import socketserver
import pathlib

class MyHandler(http.server.SimpleHTTPRequestHandler):
    html = ""

    def __init__(self, request, client_address, server, *, directory = None):
        with open(pathlib.Path(__file__).parent / 'index.html', 'r') as f:
            self.html = f.read()

        super().__init__(request, client_address, server, directory=directory)

    def do_GET(self):
        if self.path == '/':
            # Serve the HTML page with the button
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.html.encode())
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/clicked':
            # Handle button click
            print("Button was clicked!")  # This prints to the Python console
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Button click recorded')
        else:
            self.send_error(404)

PORT = 8000

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        print(f"Server running at http://localhost:{PORT}")
        print("Press Ctrl+C to stop the server")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")
        finally:
            httpd.server_close()