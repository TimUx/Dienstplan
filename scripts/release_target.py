"""Resolve an existing release to immutable source, or attach verified build assets."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def resolve_target(tag, source_sha, require_source_sha, repo):
    if not re.fullmatch(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", tag):
        raise ValueError("Release tag must have the form vMAJOR.MINOR.PATCH")
    if require_source_sha or source_sha:
        if not re.fullmatch(r"[0-9a-fA-F]{40}", source_sha):
            raise ValueError("An explicit full 40-character source SHA is required")
    # Fetch into FETCH_HEAD, never create, move or force-update a release tag.
    command("git", "fetch", "--no-tags", "origin", f"refs/tags/{tag}")
    sha = command("git", "rev-parse", "FETCH_HEAD^{commit}")
    if source_sha and sha != source_sha.lower():
        raise ValueError(f"Tag {tag} points to {sha}, not requested source {source_sha}")
    release = json.loads(command("gh", "api", f"repos/{repo}/releases/tags/{tag}"))
    if release["tag_name"] != tag or release["draft"] or not release["published_at"]:
        raise ValueError("Target must be an existing published release")
    if release.get("immutable"):
        raise ValueError("Cannot attach assets to an immutable release")
    return tag[1:], sha


def asset_names(version):
    return [
        f"Dienstplan-Windows-v{version}.zip",
        f"Dienstplan-Windows-Setup-v{version}.exe",
        f"Dienstplan-Linux-v{version}.tar.gz",
        f"dienstplan_{version}_amd64.deb",
        f"dienstplan-{version}-1.x86_64.rpm",
    ]


def publish_assets(tag, version, repo):
    names = asset_names(version)
    for name in names:
        if not Path(name).is_file() or Path(name).stat().st_size == 0:
            raise ValueError(f"Missing or empty build asset: {name}")
    # Update only assets; preserve release notes, title, status and the existing tag.
    command("gh", "release", "upload", tag, *names, "--clobber", "--repo", repo)
    release = json.loads(command("gh", "api", f"repos/{repo}/releases/tags/{tag}"))
    assets = {asset["name"]: asset for asset in release["assets"]}
    for name in names:
        asset = assets.get(name)
        if not asset or asset["state"] != "uploaded" or asset["size"] != Path(name).stat().st_size:
            raise ValueError(f"Release asset not uploaded correctly: {name}")
        with Path(name).open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        # Check actual downloadable bytes, not just release metadata or asset names.
        downloaded = subprocess.check_output(
            ["gh", "api", "-H", "Accept: application/octet-stream",
             f"repos/{repo}/releases/assets/{asset['id']}"]
        )
        if hashlib.sha256(downloaded).hexdigest() != digest:
            raise ValueError(f"Download checksum mismatch: {name}")
        print(f"Verified download: {name} (sha256:{digest})")


def main():
    mode = sys.argv[1]
    if mode not in ("resolve", "publish"):
        raise ValueError(f"Unsupported mode: {mode}")
    tag = os.environ["RELEASE_TAG"]
    repo = os.environ["GITHUB_REPOSITORY"]
    version, sha = resolve_target(
        tag, os.environ.get("SOURCE_SHA", ""),
        mode == "publish" or os.environ.get("REQUIRE_SOURCE_SHA") == "true", repo,
    )
    print(f"Release {tag}: version={version}, source={sha}")
    if mode == "resolve":
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"tag={tag}\nversion={version}\nsha={sha}\n")
    else:
        publish_assets(tag, version, repo)


if __name__ == "__main__":
    main()
