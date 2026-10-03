# pythont

Free-threaded (`--disable-gil`) CPython, built from source on
`debian:trixie-slim`, published as a Docker base image.

No official Python Docker image ships a free-threaded ("t") build for any
version — this repo exists to fill that gap with a small, reproducible
build recipe that other projects can pull in as a base image instead of
each compiling their own.

## Why build from source

CPython has supported free-threaded builds since 3.13 (PEP 703), but the
official `python` images on Docker Hub have never shipped a `t`-suffixed
variant for any version. This repo's [Dockerfile](Dockerfile) follows the
[official docker-library/python recipe](https://github.com/docker-library/python)
with `--disable-gil` added, so it tracks the same build flags, optimization
settings, and multi-arch support as the images it's modeled on.

## Supported tags

| Tag | Description |
|---|---|
| `latest`, `X.Y.Z`, `X.Y` | Built from the corresponding `vX.Y.Z` release tag, where the version matches the free-threaded CPython release it contains |

Images are multi-arch (`linux/amd64`, `linux/arm64`) and rebuilt only on
tagged releases — `latest` always tracks the newest published build, never
an unreleased commit.

## Usage

```dockerfile
FROM <dockerhub-namespace>/pythont:3.14.7 AS base
```

Pin an exact version (`3.14.7`) rather than floating on `latest` or a
`3.14`-style minor tag if your project needs reproducible builds — a new
`pythont` release changes the interpreter your image builds against with
no corresponding change in your own repo's history.

`PYTHON_GIL` is **not** set by this image — it ships CPython's own stock
free-threaded default (the GIL auto-reenables itself if an imported C
extension hasn't declared it's safe to run without it). Whether it's safe
to override that with `ENV PYTHON_GIL=0` depends entirely on what your own
image does with threads and which C extensions it loads — that's a
decision for the consuming project to make and document for itself, not
something this image should presume on everyone's behalf.

## Verifying the build

```bash
docker run --rm <dockerhub-namespace>/pythont:3.14.7 \
  python3 -c "import sys; print(sys.version); print('GIL enabled:', sys._is_gil_enabled())"
```

Should print a free-threading build identifier and `GIL enabled: False`.

## Bumping the Python version

1. Update `PYTHON_VERSION` and `PYTHON_SHA256` in the [Dockerfile](Dockerfile)
   — the sha256 is published alongside each release on
   [python.org/downloads](https://www.python.org/downloads/).
2. Commit and push a tag matching the new version, e.g.:
   ```bash
   git tag v3.14.8
   git push origin v3.14.8
   ```
3. `.github/workflows/release.yml` builds and publishes `3.14.8`, `3.14`,
   and `latest` from that tag.

## License & issues

See the [source repository](https://github.com/rackitio/pythont) to file
issues or contribute.
