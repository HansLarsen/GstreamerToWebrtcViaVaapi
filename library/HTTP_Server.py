from http.server import HTTPServer, SimpleHTTPRequestHandler
import pathlib

class MyHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Read the HTML file
        html_file = pathlib.Path(__file__).parent / 'index.html'
        with open(html_file, 'r') as f:
            self.html = f.read()
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.html.encode())
        else:
            super().do_GET()