#!/usr/bin/env python3
"""Configure Docker Hub caching in the existing local JCR instance."""
import json
from urllib.error import HTTPError
from urllib.request import Request

import bootstrap as lab

REMOTE = "docker-hub-remote"
VIRTUAL = "docker"
LOCAL = "docker-local"
UPSTREAM = "https://registry-1.docker.io/"


def request(session, path, method="GET", value=None):
    query = Request(lab.ORIGIN + "/ui/api/v1/ui" + path, method=method,
                    headers={"Content-Type": "application/json", "Origin": lab.ORIGIN,
                             "X-Requested-With": "XMLHttpRequest"},
                    data=None if value is None else json.dumps(value).encode())
    try:
        with session.open(query, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        raise SystemExit(f"Local JCR {method} {path}: HTTP {error.code}") from None


def main():
    credentials = json.loads((lab.PRIVATE / "credentials.json").read_text())
    session = lab.ui_session(credentials["admin"])
    listing = lab.api("/api/repositories", credentials["admin"])
    lab.require_success(listing, "Repository listing")
    existing = {repo["key"] for repo in json.loads(listing[1])}
    if LOCAL not in existing:
        raise SystemExit("Run bootstrap.py first to create the local repository and accounts.")
    desired = [
        {"repoName": REMOTE, "packageType": "Docker", "repoType": "REMOTE", "xrayEnabled": False},
        {"repoName": VIRTUAL, "packageType": "Docker", "repoType": "VIRTUAL", "xrayEnabled": False,
         "defaultDeploymentRepo": LOCAL, "includedLocalRepositories": [LOCAL],
         "includedRemoteRepositories": [REMOTE]},
    ]
    missing = [repo for repo in desired if repo["repoName"] not in existing]
    if missing:
        # JCR's UI onboarding API supplies its own valid Docker repository defaults.
        request(session, "/onboarding/createQuickRepos", "POST", {"repositories": missing})

    remote = request(session, f"/admin/repositories/remote/{REMOTE}")
    virtual = request(session, f"/admin/repositories/virtual/{VIRTUAL}")
    if (remote["basic"].get("url", "").rstrip("/") != UPSTREAM.rstrip("/")
            or remote["basic"].get("offline")
            or not remote["advanced"].get("storeArtifactsLocally")
            or remote["advanced"].get("blackedOut")
            or not remote["typeSpecific"].get("enableTokenAuthentication")):
        raise SystemExit("The existing Docker Hub repository differs from the expected online cache configuration.")
    if ([repo["repoName"] for repo in virtual["basic"]["selectedRepositories"]] != [LOCAL, REMOTE]
            or virtual["basic"].get("defaultDeploymentRepo") != LOCAL):
        raise SystemExit("The existing virtual repository differs from the expected local/remote configuration.")

    # Deploy/Cache on a remote permits fetching uncached upstream images.
    # Keep this separate from permissions to publish our own images in docker-local.
    permission_name = "local-docker-hub-cache"
    permission = {"name": permission_name, "resources": {"artifact": {
        "actions": {"users": {
            credentials["reader"]["username"]: ["READ", "WRITE"],
            credentials["publisher"]["username"]: ["READ", "WRITE"],
        }},
        "targets": {REMOTE: {"include_patterns": ["**"]}},
    }}}
    current = lab.ui_api("/permissions/" + permission_name, session)
    if current[0] == 404:
        lab.require_success(lab.ui_api("/permissions", session, "POST", permission), "Docker Hub cache permissions")
    else:
        lab.require_success(current, "Docker Hub cache permissions lookup")
        artifact = json.loads(current[1])["resources"]["artifact"]
        actual = {name: set(rights) for name, rights in artifact["actions"].get("users", {}).items()}
        expected = {name: set(rights) for name, rights in permission["resources"]["artifact"]["actions"]["users"].items()}
        targets = artifact["targets"]
        cache = targets.get(REMOTE, {})
        if (set(targets) != {REMOTE} or cache.get("include_patterns") != ["**"]
                or any(cache.get(field) for field in ("exclude_patterns", "include_attributes", "exclude_attributes"))
                or actual != expected or artifact["actions"].get("groups")):
            raise SystemExit("Existing Docker Hub cache permissions differ; inspect the local permission target.")
    (lab.ROOT / "docker-hub.json").write_text(json.dumps({
        "virtual_repository": VIRTUAL, "local_repository": LOCAL,
        "remote_repository": REMOTE, "upstream": UPSTREAM,
    }, indent=2) + "\n")
    print("Docker Hub cache configured: localhost:8082/docker/<image>:<tag>")


if __name__ == "__main__":
    main()
