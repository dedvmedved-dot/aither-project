#!/usr/bin/env python3
"""Aither Gateway with mTLS."""
import os, ssl, sys, socket, traceback

sys.path.insert(0, '/app')

from http.server import HTTPServer

MTLS_DIR = os.environ.get('MTLS_DIR', '/etc/mtls')
CA_CERT = os.path.join(MTLS_DIR, 'ca.crt')
SERVER_CERT = os.path.join(MTLS_DIR, 'tls.crt')
SERVER_KEY = os.path.join(MTLS_DIR, 'tls.key')

def run_mtls_server(host='0.0.0.0', port=8443):
    import gateway
    handler = gateway.Gateway

    # Create plain HTTP server first
    httpd = HTTPServer((host, port), handler)

    # Then wrap in SSL with mTLS
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
