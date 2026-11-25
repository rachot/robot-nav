"""เซิร์ฟเวอร์ HTTPS สำหรับเปิดหน้าเว็บจากมือถือในวง Wi-Fi เดียวกัน

มือถือจะใช้ GPS ได้เฉพาะเมื่อเปิดเว็บผ่าน HTTPS จึงต้องมีใบรับรอง (cert.pem / key.pem)
สร้างใบรับรองแบบ self-signed ได้ด้วย:
  openssl req -x509 -newkey rsa:2048 -nodes -days 365 -keyout key.pem -out cert.pem -subj "/CN=robot-nav"
รัน:  python serve.py [port]
"""
import http.server
import pathlib
import socket
import ssl
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8443


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def send_head(self):
        # never hand out the private key or this script
        if self.path.split("?")[0].lstrip("/").lower() in ("key.pem", "serve.py"):
            self.send_error(404)
            return None
        return super().send_head()


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.168.255.255", 1))  # no packet is sent; just picks the LAN interface
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


cert, key = ROOT / "cert.pem", ROOT / "key.pem"
if not cert.exists() or not key.exists():
    sys.exit("ไม่พบ cert.pem / key.pem — ดูวิธีสร้างที่ส่วนหัวของไฟล์นี้")

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(cert, key)
httpd = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
print(f"เปิดจากมือถือ (Wi-Fi เดียวกัน): https://{lan_ip()}:{PORT}", flush=True)
httpd.serve_forever()
