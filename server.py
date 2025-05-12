import http.server
import socketserver

class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

handler_object = MyHttpRequestHandler
PORT = 8000

my_server = socketserver.TCPServer(("", PORT), handler_object)
print(f"Server started at localhost:{PORT}")
my_server.serve_forever()