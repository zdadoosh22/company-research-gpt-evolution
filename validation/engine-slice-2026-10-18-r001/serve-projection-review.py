from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import hashlib,json,threading
root=Path(__file__).resolve().parents[2]
payload=(root/'state/research-engine/status.html').read_bytes()
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path!='/status': self.send_error(404); return
  self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(payload))); self.end_headers(); self.wfile.write(payload)
 def log_message(self,*args): pass
server=HTTPServer(('127.0.0.1',0),Handler)
print(json.dumps({'url':f'http://127.0.0.1:{server.server_port}/status','html_sha256':hashlib.sha256(payload).hexdigest(),'scope':'one frozen derived HTML response; no filesystem routing; loopback only'}),flush=True)
threading.Timer(180,server.shutdown).start()
try: server.serve_forever()
except KeyboardInterrupt: pass
finally: server.server_close()
