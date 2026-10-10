# pythont

Free-threaded (`--disable-gil`) CPython, built from source on
`debian:trixie-slim`, published as a Docker base image at
[`rackitio/pythont`](https://hub.docker.com/r/rackitio/pythont).

No official Python Docker image ships a free-threaded ("t") build for any
version — this repo exists to fill that gap with a small, reproducible
build recipe that other projects can pull in as a base image instead of
each compiling their own.

## Why build from source

CPython has supported free-threaded builds since 3.13 (PEP 703), but the
official `python` images on Docker Hub have never shipped a `t`-suffixed
variant for any version. This repo's [Dockerfile](Dockerfile) follows the
[official docker-library/python recipe](https://github.com/docker-library/python)
with `--disable-gil` added, so it tracks the same build flags and
optimization settings as the images it's modeled on.

## Tags

This repo builds **one Python version at a time**, the newest stable
release, in two channels:

- **stable** is built once per Python release and then never changes.
- **weekly** is rebuilt every Monday from the same Python version to pick up
  Debian security fixes.

| Tag | Channel | Updated when | Moves to a new minor version? |
|---|---|---|---|
| `stable`, `latest` | stable | a new Python release (patch or minor) | **yes** |
| `X.Y` (e.g. `3.15`) | stable | a new patch release of X.Y; **frozen** once the next minor ships | no |
| `X.Y.Z` (e.g. `3.15.0`) | stable | never (built once) | no |
| `weekly` | weekly | every Monday, and on each stable release | **yes** |
| `X.Y.Z-weekly` (e.g. `3.15.0-weekly`) | weekly | every Monday until the next Python release, then **frozen** | no |

When a new Python version is released, the weekly channel resets to it as
well, so `weekly` is always the current Python version with the newest
Debian packages. Tags never move backwards to an older Python version.

Images are multi-arch (`linux/amd64`, `linux/arm64`).

### Older minor versions are frozen

When a new minor version (e.g. 3.16) is released here, the previous
minor's tags (`3.15`, `3.15.Z-weekly`) **stop updating**. They get no
further Python patch releases or Debian security fixes from this repo.
Downstream projects have to move to the new minor version themselves.

### Which tag should I use?

| You want | Use |
|---|---|
| Security fixes, no surprise Python upgrades | `X.Y` (e.g. `3.15`) for Python patches, or `X.Y.Z-weekly` for Debian patches too. Move to the next minor yourself when it ships, since these tags freeze then. |
| Always the newest of everything | `weekly` |
| A build that never changes | `X.Y.Z`, or pin any tag by digest (`rackitio/pythont@sha256:…`; digests are in each GitHub release) |

**Don't follow `latest`, `stable` or `weekly` in production** unless you're
ready for a minor-version jump. When a new minor version ships, those tags
move to it. C extensions built for the old minor (e.g. `cp314t` wheels)
won't load on the new one, and some standard-library modules get removed
between minor versions. Watch the
[releases](https://github.com/rackitio/pythont/releases) to know when an
`X.Y` tag you use has frozen.

## Usage

```dockerfile
FROM rackitio/pythont:3.15
```

`PYTHON_GIL` is **not** set by this image — it ships CPython's own stock
free-threaded default (the GIL auto-reenables itself if an imported C
extension hasn't declared it's safe to run without it). Whether it's safe
to override that with `ENV PYTHON_GIL=0` depends entirely on what your own
image does with threads and which C extensions it loads — that's a
decision for the consuming project to make and document for itself, not
something this image should presume on everyone's behalf.

## Verifying the build

```bash
docker run --rm rackitio/pythont:3.15 \
  python3 -c "import sys; print(sys.version); print('GIL enabled:', sys._is_gil_enabled())"
```

Should print a free-threading build identifier and `GIL enabled: False`.

## What changed in each build

Every published build gets a
[GitHub release](https://github.com/rackitio/pythont/releases):
`vX.Y.Z` for stable, `weekly-YYYYMMDD` (pre-release) for weekly. The notes
list:

- the Python version change, with a changelog link;
- every Debian package added, removed or upgraded compared with the image
  the tag pointed to before;
- a Trivy vulnerability scan before and after, listing CVEs fixed, newly
  reported, and still open.

### Known open CVEs

Trivy reports a few CVEs in `msgpack`, `setuptools` and `urllib3`. These
are the copies pip bundles inside itself (`pip/_vendor`), not packages
installed in the image, and they're only reachable when pip itself runs.
They clear when pip ships a release with updated bundled libraries. Most
Debian CVEs listed have no Debian fix yet. The weekly build picks up fixes
as Debian publishes them.

## How releases happen

| Workflow | Trigger | Does |
|---|---|---|
| [python-update](.github/workflows/python-update.yml) | daily | Checks python.org for a new stable release. Verifies the tarball's sha256 and Sigstore signature, opens a PR bumping the [Dockerfile](Dockerfile), and runs a test build on it. |
| [ci](.github/workflows/ci.yml) | PRs | Test-builds both architectures without publishing. |
| [release](.github/workflows/release.yml) | push to `main` that changes `PYTHON_VERSION` (i.e. merging an update PR) | Publishes the stable channel and creates the `vX.Y.Z` release. |
| [weekly](.github/workflows/weekly.yml) | Mondays 06:00 UTC | Rebuilds the current version and publishes the weekly channel. |
| [dockerhub-description](.github/workflows/dockerhub-description.yml) | push to `main` that changes [DOCKERHUB.md](DOCKERHUB.md) | Updates the Docker Hub overview page. |

Each build runs natively per architecture with no layer cache, so every
image gets current Debian packages. `release` and `weekly` can also be run
by hand from the Actions tab.

### Releasing a new Python version

1. python-update opens a PR titled **Bump Python to X.Y.Z** (or an issue
   of the same name with a one-click link to create that PR; see
   [Repository setup](#repository-setup)). A new minor version gets a
   warning in the PR body, because merging moves `stable`, `latest` and
   `weekly` to it and freezes the old minor's tags.
2. Wait for the **ci** check to pass, then merge.
3. release publishes the images and the `vX.Y.Z` release notes.

If a patch release and a new minor arrive together (e.g. 3.14.8 and
3.15.0), the patch PR says so. **Merge the patch first**, so the old
minor's tags freeze on its final patch. Merging it after the new minor is
refused, because tags never move backwards. The new minor's branch will
then conflict: delete its `python-update/X.Y.Z` branch and re-run
python-update to recreate it.

To bump by hand, run
`python3 .github/scripts/check_python_release.py apply X.Y.Z` (needs
`pip install sigstore`) and open a PR. Before a new minor version's first
release, add its release manager's Sigstore identity to `SIGNERS` in
[check_python_release.py](.github/scripts/check_python_release.py), from
[python.org/downloads/metadata/sigstore](https://www.python.org/downloads/metadata/sigstore/).

### Repository setup

- Secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`. The token needs
  **Read, Write & Delete** scope if dockerhub-description should work;
  Read & Write is enough for pushing images.
- Optional: Settings → Actions → General → **Allow GitHub Actions to
  create and approve pull requests**, so python-update can open PRs
  itself. In the rackitio organization an org owner has to allow this at
  the org level first (the repo checkbox is greyed out until they do).
  While it's off, python-update opens an issue with a link that creates the
  PR pre-filled.

## License & issues

See the [source repository](https://github.com/rackitio/pythont) to file
issues or contribute.
