#!/usr/bin/env python3
"""Initialize only the loopback JCR lab and save its credentials privately."""
import base64
import json
import http.cookiejar
import os
from pathlib import Path
import secrets
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler, HTTPCookieProcessor
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
PRIVATE = ROOT / "secrets"
ORIGIN = "http://" + os.environ.get("DEMO_ADMIN_HOST", "127.0.0.1") + ":8082"
BASE = ORIGIN + "/artifactory"
# This lab never routes local administration through a corporate proxy.
HTTP = build_opener(ProxyHandler({}))


def private_file(name, content):
    path = PRIVATE / name
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(content)
    path.chmod(0o600)


def api(path, credentials, method="GET", data=None):
    encoded = base64.b64encode(f"{credentials['username']}:{credentials['password']}".encode()).decode()
    request = Request(BASE + path, method=method, headers={
        "Authorization": "Basic " + encoded, "Content-Type": "application/json",
    }, data=None if data is None else json.dumps(data).encode())
    try:
        with HTTP.open(request, timeout=30) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()


def require_success(result, operation):
    if not 200 <= result[0] < 300:
        detail = result[1].decode(errors="replace")
        credentials_path = PRIVATE / "credentials.json"
        if credentials_path.exists():
            for account in json.loads(credentials_path.read_text()).values():
                detail = detail.replace(account["password"], "[redacted]")
        raise SystemExit(f"{operation} failed with HTTP {result[0]}: {detail[:1000]}")


def ui_session(admin):
    """Automate JCR's available UI administration; public mutation APIs need Pro."""
    session = build_opener(ProxyHandler({}), HTTPCookieProcessor(http.cookiejar.CookieJar()))
    request = Request(ORIGIN + "/ui/api/v1/ui/auth/login", method="POST",
        headers={"Content-Type": "application/json", "Origin": ORIGIN,
                 "X-Requested-With": "XMLHttpRequest"},
        data=json.dumps({"user": admin["username"], "password": admin["password"], "type": "login"}).encode())
    with session.open(request, timeout=30) as response:
        if not json.load(response).get("admin"):
            raise SystemExit("Local JCR administration login did not grant administrator access.")
    return session


def ui_api(path, session, method="GET", data=None):
    request = Request(ORIGIN + "/ui/api/v1/access/api/ui" + path, method=method,
        headers={"Content-Type": "application/json", "Origin": ORIGIN,
                 "X-Requested-With": "XMLHttpRequest"},
        data=None if data is None else json.dumps(data).encode())
    try:
        with session.open(request, timeout=30) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()


def create_local_repository(session):
    """Use the authenticated onboarding API shipped with this pinned JCR version."""
    request = Request(ORIGIN + "/ui/api/v1/ui/onboarding/createQuickRepos", method="POST",
        headers={"Content-Type": "application/json", "Origin": ORIGIN,
                 "X-Requested-With": "XMLHttpRequest"},
        data=json.dumps({"repositories": [{"repoName": "docker-local", "packageType": "Docker",
                                           "repoType": "LOCAL", "xrayEnabled": False}]}).encode())
    with session.open(request, timeout=30) as response:
        response.read()



def configure_account(session, account, permission_name, rights):
    user = {
        "username": account["username"], "email": account["username"] + "@localhost.invalid",
        "password": account["password"], "admin": False,
        "profileUpdatable": False, "disableUiAccess": True, "groups": [],
    }
    existing = ui_api("/users/" + account["username"], session)
    if existing[0] == 404:
        require_success(ui_api("/users", session, "POST", user), "Local publisher creation")
    else:
        require_success(existing, "Local publisher lookup")
        current = json.loads(existing[1])
        current.update(user)
        require_success(ui_api("/users/" + account["username"], session, "PUT", current), "Local publisher configuration")
    permission = {
        "name": permission_name,
        "resources": {"artifact": {
            "actions": {"users": {account["username"]: rights}},
            "targets": {"docker-local": {"include_patterns": ["**"]}},
        }},
    }
    existing = ui_api("/permissions/" + permission_name, session)
    if existing[0] == 404:
        require_success(ui_api("/permissions", session, "POST", permission), "Repository publisher permissions")
    else:
        require_success(existing, "Publisher permission lookup")
        current = json.loads(existing[1])["resources"]["artifact"]
        if (set(current["targets"]) != {"docker-local"}
                or set(current["actions"]["users"].get(account["username"], []))
                != set(rights)):
            raise SystemExit("Existing publisher permission differs; review it in the local JCR UI.")



def main():
    PRIVATE.mkdir(mode=0o700, exist_ok=True)
    PRIVATE.chmod(0o700)
    path = PRIVATE / "credentials.json"
    if path.exists():
        credentials = json.loads(path.read_text())
    else:
        credentials = {
            "admin": {"username": "admin", "password": secrets.token_urlsafe(32)},
            "publisher": {"username": "local-builder", "password": secrets.token_urlsafe(32)},
        }
        # Save before changing passwords so a failed/interrupted run is resumable.
        private_file("credentials.json", json.dumps(credentials, indent=2) + "\n")

    admin = credentials["admin"]
    status, _ = api("/api/repositories", admin)
    if status == 401:
        initial = {"username": "admin", "password": "password"}
        require_success(api("/api/security/users/authorization/changePassword", initial, "POST", {
            "userName": "admin", "oldPassword": "password",
            "newPassword1": admin["password"], "newPassword2": admin["password"],
        }), "Initial administrator password change")
    require_success(api("/api/repositories", admin), "Administrator authentication")

    repositories = api("/api/repositories", admin)
    require_success(repositories, "Repository listing")
    existing_keys = {repository["key"] for repository in json.loads(repositories[1])}
    if "docker-local" not in existing_keys:
        create_local_repository(ui_session(admin))
        repositories = api("/api/repositories", admin)
        require_success(repositories, "Created repository lookup")
        if not any(repository["key"] == "docker-local" for repository in json.loads(repositories[1])):
            raise SystemExit("Docker repository was not created; inspect Artifactory startup logs.")

    credentials.setdefault("reader", {"username": "local-reader", "password": secrets.token_urlsafe(32)})
    private_file("credentials.json", json.dumps(credentials, indent=2) + "\n")
    session = ui_session(admin)
    configure_account(session, credentials["publisher"], "local-docker-publisher", ["READ", "WRITE", "DELETE", "ANNOTATE"])
    configure_account(session, credentials["reader"], "local-docker-reader", ["READ"])
    publisher = credentials["publisher"]
    reader = credentials["reader"]
    auth = base64.b64encode((reader["username"] + ":" + reader["password"]).encode()).decode()
    private_file("docker-read.json", json.dumps({"auths": {
        "localhost:8082": {"auth": auth}, "host.docker.internal:8082": {"auth": auth},
    }}, separators=(",", ":")))
    private_file("publisher-password", publisher["password"])

    private_file("maven-settings.xml", f'''<settings xmlns="http://maven.apache.org/SETTINGS/1.2.0">
  <servers>
    <server>
      <id>localhost:8082</id>
      <username>{escape(publisher['username'])}</username>
      <password>{escape(publisher['password'])}</password>
    </server>
    <server>
      <id>host.docker.internal:8082</id>
      <username>{escape(publisher['username'])}</username>
      <password>{escape(publisher['password'])}</password>
    </server>
  </servers>
</settings>
''')
    print("Local docker-local repository and local-builder account are ready.")
    print("Credentials and Maven settings are in infra/artifactory/secrets/ (private, ignored).")


if __name__ == "__main__":
    main()
