# pythont: free-threaded CPython

Free-threaded (`--disable-gil`, PEP 703) CPython built from source on
`debian:trixie-slim`, for `linux/amd64` and `linux/arm64`. It follows the
official `python` image recipe with `--disable-gil` added. No official
Python image ships a free-threaded build.

Source, build recipe and release notes:
[github.com/rackitio/pythont](https://github.com/rackitio/pythont)

## Tags

- **stable** is built once per Python release and then never changes.
- **weekly** is rebuilt every Monday from the same Python version to pick
  up Debian security fixes.

| Tag | Updated when | Moves to a new minor version? |
|---|---|---|
| `stable`, `latest` | a new Python release | **yes** |
| `3.14` | a new 3.14.x release | no |
| `3.14.8` | never (built once) | no |
| `weekly` | every Monday, and on each stable release | **yes** |
| `3.14.8-weekly` | every Monday until 3.14.9 ships | no |

**For production, use `3.14`** (or `3.14.Z-weekly` for weekly Debian
fixes). `latest`, `stable` and `weekly` jump to Python 3.15 when it ships,
and C extensions built for 3.14 won't load on 3.15.

## Usage

```dockerfile
FROM rackitio/pythont:3.14
```

```bash
docker run --rm rackitio/pythont:3.14 \
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
