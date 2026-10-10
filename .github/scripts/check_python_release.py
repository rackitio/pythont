#!/usr/bin/env python3
"""Find new stable CPython releases and apply one to the Dockerfile.

    check_python_release.py candidates
        Print a JSON list of versions newer than the Dockerfile's
        PYTHON_VERSION: the newest patch of the current minor, plus the
        newest release of a newer minor if there is one.

    check_python_release.py apply VERSION
        Download the source tarball, check it against the sha256 python.org
        publishes, verify its Sigstore signature against the release
        manager's identity, then rewrite PYTHON_VERSION / PYTHON_SHA256.

Free-threading is a configure flag (--disable-gil), not a separate
release, so this tracks ordinary CPython releases.
"""

import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.request

API = "https://www.python.org/api/v2/downloads"
DOCKERFILE = pathlib.Path(__file__).resolve().parents[2] / "Dockerfile"

# Release managers sign each minor line's tarballs with Sigstore. Source:
# https://www.python.org/downloads/metadata/sigstore/ -- add the new
# minor's entry there before its first release can be applied.
SIGNERS = {
    "3.13": "thomas@python.org",
    "3.14": "hugo@python.org",
    "3.15": "hugo@python.org",
}
OIDC_ISSUER = "https://github.com/login/oauth"


def get_json(url):
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.load(resp)


def parse(version):
    return tuple(int(part) for part in version.split("."))


def current_version():
    match = re.search(r"^ENV PYTHON_VERSION=(\S+)$", DOCKERFILE.read_text(), re.M)
    return match.group(1)


def stable_releases():
    releases = get_json(f"{API}/release/?is_published=true&pre_release=false")
    versions = []
    for release in releases:
        match = re.fullmatch(r"Python (3\.\d+\.\d+)", release["name"])
        if match:
            versions.append(parse(match.group(1)))
    return versions


def candidates():
    current = parse(current_version())
    releases = stable_releases()
    found = []
    same_minor = max((v for v in releases if v[:2] == current[:2]), default=current)
    if same_minor > current:
        found.append(same_minor)
    newest = max(releases)
    if newest[:2] > current[:2]:
        found.append(newest)
    return [".".join(map(str, v)) for v in found]


def source_tarball(version):
    name = f"Python-{version}.tar.xz"
    for f in get_json(f"{API}/release_file/?os=3"):
        if f["url"].endswith("/" + name) and f["sha256_sum"] and f["sigstore_bundle_file"]:
            return f
    sys.exit(f"python.org lists no sha256 + Sigstore bundle for {name}")


def download(url, dest):
    with urllib.request.urlopen(url, timeout=300) as resp, open(dest, "wb") as out:
        while chunk := resp.read(1 << 20):
            out.write(chunk)


def apply(version):
    minor = ".".join(version.split(".")[:2])
    signer = SIGNERS.get(minor)
    if not signer:
        sys.exit(
            f"No Sigstore signer known for Python {minor}; add it to SIGNERS "
            "from https://www.python.org/downloads/metadata/sigstore/"
        )
    meta = source_tarball(version)
    with tempfile.TemporaryDirectory() as tmp:
        tarball = pathlib.Path(tmp, f"Python-{version}.tar.xz")
        bundle = pathlib.Path(tmp, tarball.name + ".sigstore")
        download(meta["url"], tarball)
        download(meta["sigstore_bundle_file"], bundle)

        digest = hashlib.sha256(tarball.read_bytes()).hexdigest()
        if digest != meta["sha256_sum"]:
            sys.exit(f"sha256 mismatch for {tarball.name}: got {digest}, python.org says {meta['sha256_sum']}")

        subprocess.run(
            [
                sys.executable, "-m", "sigstore", "verify", "identity",
                "--bundle", str(bundle),
                "--cert-identity", signer,
                "--cert-oidc-issuer", OIDC_ISSUER,
                str(tarball),
            ],
            check=True,
        )

    text = DOCKERFILE.read_text()
    text = re.sub(r"^ENV PYTHON_VERSION=\S+$", f"ENV PYTHON_VERSION={version}", text, flags=re.M)
    text = re.sub(r"^ENV PYTHON_SHA256=\S+$", f"ENV PYTHON_SHA256={digest}", text, flags=re.M)
    DOCKERFILE.write_text(text)
    print(f"Dockerfile updated to Python {version} (sha256 {digest}, signed by {signer})")


if __name__ == "__main__":
    if sys.argv[1:] == ["candidates"]:
        print(json.dumps(candidates()))
    elif len(sys.argv) == 3 and sys.argv[1] == "apply":
        apply(sys.argv[2])
    else:
        sys.exit(__doc__)
