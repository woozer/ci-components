#!/usr/bin/env python3
"""Review and explicitly accept the EULA of this local JCR installation."""
import argparse
import hmac
import json
import secrets
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs
from urllib.request import Request

from bootstrap import PRIVATE, ROOT, ui_session


def submit_acceptance(session, endpoint):
    request = Request(endpoint + "/accept", method="POST", data=b"{}",
                      headers={"Origin": "http://127.0.0.1:8082",
                               "Content-Type": "application/json",
                               "X-Requested-With": "XMLHttpRequest"})
    with session.open(request, timeout=30) as response:
        if not 200 <= response.status < 300:
            raise SystemExit(f"Acceptance returned HTTP {response.status}.")
    print("Artifactory accepted the EULA submission. Refresh http://localhost:8082.", flush=True)


def browser_acceptance(session, endpoint, content):
    """Keep administrator credentials server-side; require an explicit browser submission."""
    token = secrets.token_urlsafe(32)
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Accept the local JFrog EULA</title>
<style>
body{font:17px system-ui,sans-serif;max-width:960px;margin:32px auto;padding:0 24px;color:#182027}
iframe{width:100%;height:55vh;border:1px solid #aaa;border-radius:6px;background:white}
label{display:block;margin:24px 0;line-height:1.6}input{width:20px;height:20px;vertical-align:middle}
button{font:inherit;background:#146b36;color:white;border:0;border-radius:6px;padding:14px 22px;cursor:pointer}
.note{color:#485560;font-size:15px}
</style>
<h1>Review and accept the JFrog EULA</h1>
<p>This page submits your acceptance to your local Artifactory instance at
<strong>http://localhost:8082</strong>.</p>
<iframe title="JFrog EULA from your local Artifactory" src="/agreement" sandbox></iframe>
<form action="/accept" method="post">
<input type="hidden" name="token" value="__TOKEN__">
<label><input type="checkbox" name="accept" value="yes" required>
I have read and agree to the JFrog EULA for this local JCR installation.</label>
<button type="submit">Accept EULA in Artifactory</button>
</form>
<p class="note">Close this page to leave the agreement unsigned. This is a local setup helper;
administrator credentials remain on this computer and are never sent to this page.</p></html>'''.replace("__TOKEN__", token)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, body):
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy",
                             "default-src 'none'; style-src 'unsafe-inline'; frame-src 'self'; "
                             "form-action 'self'; base-uri 'none'; frame-ancestors 'self'")
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self):
            if self.headers.get("Host") != origin.removeprefix("http://"):
                self.reply(403, "Unexpected host.")
            elif self.path == "/":
                self.reply(200, page)
            elif self.path == "/agreement":
                self.reply(200, content)
            else:
                self.reply(404, "Not found.")

        def do_POST(self):
            if (self.path != "/accept" or self.headers.get("Origin") != origin
                    or self.headers.get("Host") != origin.removeprefix("http://")):
                self.reply(403, "Open the local review page to submit acceptance.")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 4096:
                    raise ValueError()
                fields = parse_qs(self.rfile.read(length).decode("utf-8"))
            except (ValueError, UnicodeError):
                self.reply(400, "Invalid acceptance submission.")
                return
            if (fields.get("accept") != ["yes"] or len(fields.get("token", [])) != 1
                    or not hmac.compare_digest(fields["token"][0], token)):
                self.reply(400, "Return to the review page and select the agreement checkbox to accept.")
                return
            try:
                submit_acceptance(session, endpoint)
            except HTTPError as error:
                self.reply(502, f"Artifactory returned HTTP {error.code}. Return to the review page to retry.")
                return
            except URLError:
                self.reply(502, "Cannot reach local Artifactory. Return to the review page to retry.")
                return
            self.reply(200, '<h1>Acceptance submitted to Artifactory</h1>'
                       '<p>You can close this page and return to the chat.</p>'
                       '<p><a href="http://localhost:8082">Open Artifactory</a></p>')
            server.accepted = True

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        origin = f"http://127.0.0.1:{server.server_port}"
        server.accepted = False
        server.timeout = 1
        print(f"Review and accept in your browser: {origin}", flush=True)
        webbrowser.open(origin)
        try:
            while not server.accepted:
                server.handle_request()
        except KeyboardInterrupt:
            print("\nBrowser helper stopped.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view-only", action="store_true",
                        help="download the agreement without opening a browser or accepting it")
    parser.add_argument("--browser", action="store_true",
                        help="open a local review page with a button that submits acceptance to Artifactory")
    args = parser.parse_args()
    credentials = json.loads((PRIVATE / "credentials.json").read_text())
    session = ui_session(credentials["admin"])
    endpoint = "http://127.0.0.1:8082/ui/api/v1/ui/jcr/eula"
    with session.open(endpoint, timeout=30) as response:
        content = json.load(response)["content"]
    if not isinstance(content, str) or not content.strip():
        raise SystemExit("Artifactory returned an empty agreement; nothing was accepted.")
    agreement = ROOT / "eula.html"
    agreement.write_text(content, encoding="utf-8")
    print(f"Agreement from your local JCR: {agreement}", flush=True)
    if args.view_only:
        print("View only: nothing was accepted.")
        return
    if args.browser:
        browser_acceptance(session, endpoint, content)
        return
    if not sys.stdin.isatty():
        raise SystemExit("Run interactively in your terminal to review and accept the agreement.")
    webbrowser.open(agreement.as_uri())
    print("Review the agreement in your browser before continuing.")
    try:
        answer = input("To agree to the JFrog EULA for this local JCR, type ACCEPT (Enter cancels): ")
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled. Nothing was accepted.")
        return
    if answer.strip() != "ACCEPT":
        print("Cancelled. Nothing was accepted.")
        return
    submit_acceptance(session, endpoint)


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        raise SystemExit(f"Local Artifactory returned HTTP {error.code}; no credentials were printed.")
    except URLError as error:
        raise SystemExit(f"Cannot reach local Artifactory: {error.reason}")
