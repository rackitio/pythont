#!/usr/bin/env python3
"""Write release notes comparing a new image against the one it replaces.

Inputs are produced by the publish job in build.yml:
  --old-packages / --new-packages   `dpkg-query -W` output (Package<TAB>Version)
  --old-trivy / --new-trivy         `trivy image --format json` output
Old inputs may be empty files when there is no previous image.
"""

import argparse
import collections
import json
import pathlib

SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]


def read_packages(path):
    packages = {}
    for line in pathlib.Path(path).read_text().splitlines():
        if "\t" in line:
            name, version = line.split("\t", 1)
            packages[name] = version
    return packages


def read_vulns(path):
    text = pathlib.Path(path).read_text().strip()
    if not text:
        return {}
    vulns = {}
    for result in json.loads(text).get("Results", []):
        for v in result.get("Vulnerabilities") or []:
            vulns[(v["VulnerabilityID"], v["PkgName"])] = v
    return vulns


def vuln_line(v):
    fix = f", fixed in {v['FixedVersion']}" if v.get("FixedVersion") else ""
    return f"- `{v['VulnerabilityID']}` {v['Severity']} in `{v['PkgName']}` {v['InstalledVersion']}{fix}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--channel", required=True)
    p.add_argument("--image", required=True)
    p.add_argument("--digest", required=True)
    p.add_argument("--tags", required=True)
    p.add_argument("--python-new", required=True)
    p.add_argument("--python-old", default="")
    p.add_argument("--old-ref", default="")
    p.add_argument("--old-packages", required=True)
    p.add_argument("--new-packages", required=True)
    p.add_argument("--old-trivy", required=True)
    p.add_argument("--new-trivy", required=True)
    a = p.parse_args()

    out = []
    out.append(f"**Channel:** `{a.channel}`  ")
    out.append(f"**Image:** `{a.image}@{a.digest}`  ")
    out.append("**Tags:** " + ", ".join(f"`{t}`" for t in a.tags.split()) + "  ")
    if a.old_ref:
        out.append(f"**Compared with:** `{a.old_ref}`")
    else:
        out.append("**Compared with:** nothing (first build of this channel)")

    out.append("\n### Python\n")
    if a.python_old and a.python_old != a.python_new:
        out.append(
            f"{a.python_old} → **{a.python_new}** "
            f"([changelog](https://docs.python.org/release/{a.python_new}/whatsnew/changelog.html))"
        )
        if a.python_old.split(".")[:2] != a.python_new.split(".")[:2]:
            out.append(
                "\n> **New minor version.** C extensions built for "
                f"{'.'.join(a.python_old.split('.')[:2])} will not load; rebuild or reinstall wheels."
            )
    else:
        out.append(f"{a.python_new} (unchanged)")

    out.append("\n### Debian packages (linux/amd64)\n")
    old, new = read_packages(a.old_packages), read_packages(a.new_packages)
    if not old:
        out.append(f"{len(new)} packages installed; no previous image to compare.")
    else:
        rows = []
        for name in sorted(old.keys() | new.keys()):
            before, after = old.get(name), new.get(name)
            if before != after:
                change = "added" if before is None else "removed" if after is None else "upgraded"
                rows.append(f"| `{name}` | {before or '—'} | {after or '—'} | {change} |")
        if rows:
            out.append("| Package | Before | After | Change |")
            out.append("|---|---|---|---|")
            out.extend(rows)
        else:
            out.append("No Debian package changes.")

    out.append("\n### Vulnerabilities (Trivy, linux/amd64)\n")
    old_v, new_v = read_vulns(a.old_trivy), read_vulns(a.new_trivy)
    old_c = collections.Counter(v["Severity"] for v in old_v.values())
    new_c = collections.Counter(v["Severity"] for v in new_v.values())
    out.append("| | " + " | ".join(SEVERITIES) + " | Total |")
    out.append("|---|" + "---|" * (len(SEVERITIES) + 1))
    if old_v:
        out.append("| Before | " + " | ".join(str(old_c[s]) for s in SEVERITIES) + f" | {len(old_v)} |")
    out.append("| After | " + " | ".join(str(new_c[s]) for s in SEVERITIES) + f" | {len(new_v)} |")

    fixed = [old_v[k] for k in sorted(old_v.keys() - new_v.keys())]
    added = [new_v[k] for k in sorted(new_v.keys() - old_v.keys())]
    fixable = [v for k, v in sorted(new_v.items()) if v.get("FixedVersion")]
    if fixed:
        out.append(f"\n**Fixed by this build ({len(fixed)}):**\n")
        out.extend(vuln_line(v) for v in fixed)
    if old_v and added:
        out.append(
            f"\n**Newly reported ({len(added)}):** new packages, or CVEs published "
            "since the previous build was scanned.\n"
        )
        out.extend(vuln_line(v) for v in added)
    if fixable:
        out.append(
            f"\n**Open with an upstream fix not yet in this image ({len(fixable)}):** "
            "usually libraries bundled inside pip, which clear when pip ships a release.\n"
        )
        out.extend(vuln_line(v) for v in fixable)

    print("\n".join(out))


if __name__ == "__main__":
    main()
