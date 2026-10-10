# pythont: free-threaded CPython

Free-threaded (`--disable-gil`, PEP 703) CPython built from source on
`debian:trixie-slim`, for `linux/amd64` and `linux/arm64`. It follows the
official `python` image recipe with `--disable-gil` added. No official
Python image ships a free-threaded build.

Source, build recipe and release notes:
[github.com/rackitio/pythont](https://github.com/rackitio/pythont)

## Tags

One Python version is built at a time, the newest stable release:

- **stable** is built once per Python release and then never changes.
- **weekly** is rebuilt every Monday from the same Python version to pick
  up Debian security fixes.

| Tag | Updated when | Moves to a new minor version? |
|---|---|---|
| `stable`, `latest` | a new Python release | **yes** |
| `3.15` | a new 3.15.x release; frozen once 3.16 ships | no |
| `3.15.0` | never (built once) | no |
| `weekly` | every Monday, and on each stable release | **yes** |
| `3.15.0-weekly` | every Monday until the next Python release, then frozen | no |

**For production, pin a minor version such as `3.15`** (or `3.15.Z-weekly`
for weekly Debian fixes). `latest`, `stable` and `weekly` jump to each new
minor version, and C extensions built for one minor won't load on the next.
**Older minor versions are frozen**: when 3.16 ships here, `3.15` stops
getting updates, so move up yourself.

## Usage

```dockerfile
FROM rackitio/pythont:3.15
```

```bash
docker run --rm rackitio/pythont:3.15 \
  python3 -c "import sys; print(sys.version, 'GIL enabled:', sys._is_gil_enabled())"
```

`PYTHON_GIL` is not set. CPython's default applies: the GIL turns back on
if an imported C extension hasn't declared it's safe to run without it.

## What changed in each build

Every build has a
[GitHub release](https://github.com/rackitio/pythont/releases) listing the
Python version change, every Debian package that changed, and a Trivy
before/after vulnerability scan. Image digests for pinning are in the
release notes.
