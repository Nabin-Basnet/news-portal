"""Run separate local HTTP and HTTPS development servers."""
from __future__ import annotations
import ssl
import threading
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.wsgi import get_wsgi_application

class Command(BaseCommand):
    help = "Run HTTP and HTTPS development servers concurrently."

    def add_arguments(self, parser):
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--http-port", type=int, default=8000)
        parser.add_argument("--https-port", type=int, default=8443)
        parser.add_argument("--certfile", default=str(settings.BASE_DIR / ".certs" / "localhost-cert.pem"))
        parser.add_argument("--keyfile", default=str(settings.BASE_DIR / ".certs" / "localhost-key.pem"))

    def handle(self, *args, **options):
        certfile, keyfile = Path(options["certfile"]), Path(options["keyfile"])
        if not certfile.is_file() or not keyfile.is_file():
            raise CommandError("HTTPS certificate files were not found. Create them with `python manage.py generate_dev_cert`, then run this command again.")
        host, application = options["host"], get_wsgi_application()
        http_server = make_server(host, options["http_port"], application, handler_class=WSGIRequestHandler)
        https_server = make_server(host, options["https_port"], application, handler_class=WSGIRequestHandler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=certfile, keyfile=keyfile)
        https_server.socket = context.wrap_socket(https_server.socket, server_side=True)
        self.stdout.write(self.style.SUCCESS(f"HTTP:  http://{host}:{options['http_port']}/api/docs/"))
        self.stdout.write(self.style.SUCCESS(f"HTTPS: https://{host}:{options['https_port']}/api/docs/"))
        self.stdout.write("Press CTRL+C to stop both servers.")
        http_thread = threading.Thread(target=http_server.serve_forever, daemon=True)
        http_thread.start()
        try:
            https_server.serve_forever()
        except KeyboardInterrupt:
            self.stdout.write("\nStopping development servers...")
        finally:
            http_server.shutdown()
            https_server.shutdown()
            http_server.server_close()
            https_server.server_close()


