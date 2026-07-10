#!/usr/bin/env python3
"""Aither Gateway with mTLS."""
import os, ssl, sys, socket, traceback

sys.path.insert(0, '/app')

from http.server import HTTPServer

MTLS_DIR = os.environ.get('MTLS_DIR', '/etc/mtls')
CA_CERT = os.path.join(MTLS_DIR, 'ca.crt')
SERVER_CERT = os.path.join(MTLS_DIR, 'tls.crt')
SERVER_KEY = os.path.join(MTLS_DIR, 'tls.key')

def run_mtls_server(host='0.0.0.0', port=8443, http_port=8080):
    import gateway
    import threading
    handler = gateway.Gateway

    # Start plain HTTP server for internal cluster traffic
    httpd_plain = HTTPServer((host, http_port), handler)
    t = threading.Thread(target=httpd_plain.serve_forever, daemon=True)
    t.start()
    print(f"[http] Gateway listening on http://{host}:{http_port} (plain HTTP, cluster-only)", flush=True)

    # Create HTTPS server with mTLS
    httpd = HTTPServer((host, port), handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = False
    try:
        ctx.load_verify_locations(cafile=CA_CERT)
        ctx.load_cert_chain(certfile=SERVER_CERT, keyfile=SERVER_KEY)
    except Exception as e:
        print(f"[mtls] SSL cert load error: {e}", flush=True)
        traceback.print_exc()
        raise

    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)

    print(f"[mtls] Gateway listening on https://{host}:{port} (mTLS enabled)", flush=True)
    httpd.serve_forever()

if __name__ == '__main__':
    try:
        run_mtls_server()
    except Exception as e:
        print(f"[mtls] FATAL: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
