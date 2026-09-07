"""Write an AthenaPK athinput from a verified template.

Written in Python rather than sed on purpose: the sed approach in ladder.sh set
the mesh nx2 and then the meshblock pass matched the same line and overwrote it,
which silently ran level 3 at 32x8x32 instead of 32x64x32. Here the mesh block
and the meshblock block are addressed by occurrence, so they cannot collide.

usage: mkinput.py <template> <out> <nx1> <nx2> <nx3> <mb> <tlim> <dt> <chi> <vwind> [cooling_table]
"""
import re
import sys

tpl, out = sys.argv[1], sys.argv[2]
nx1, nx2, nx3, mb = (int(v) for v in sys.argv[3:7])
tlim, dt, chi, vwind = (float(v) for v in sys.argv[7:11])
cool = sys.argv[11] if len(sys.argv) > 11 else ""

lines = open(tpl).read().split("\n")
if cool or re.search(r"^\s*<cooling>\s*$", "\n".join(lines), re.M):
    raise SystemExit(
        "REFUSED: legacy cooling input generation is retired. Its old block did "
        "not enable cooling and used nonphysical CGS temperatures. No output was "
        "written. A reviewed physical-unit setup, cooling table provenance, "
        "temperature bounds and native cooling validation are required. "
        "See analysis/followup_20260907/README.md."
    )
seen = {"nx1": 0, "nx2": 0, "nx3": 0}
out_lines = []
for ln in lines:
    m = re.match(r"^(nx[123])\s*=", ln)
    if m:
        k = m.group(1)
        seen[k] += 1
        v = {"nx1": nx1, "nx2": nx2, "nx3": nx3}[k] if seen[k] == 1 else mb
        out_lines.append("%s = %d" % (k, v))
        continue
    if re.match(r"^tlim\s*=", ln):
        out_lines.append("tlim = %.6f" % tlim); continue
    if re.match(r"^dt\s*=", ln):
        out_lines.append("dt = %.6f" % dt); continue
    if re.match(r"^rho_cloud_cgs\s*=", ln):
        out_lines.append("rho_cloud_cgs = %.1f" % chi); continue
    if re.match(r"^v_wind_cgs\s*=", ln):
        out_lines.append("v_wind_cgs = %.9f" % vwind); continue
    out_lines.append(ln)

text = "\n".join(out_lines)

open(out, "w").write(text)

# fail loudly rather than silently running the wrong grid
chk = {}
for ln in text.split("\n"):
    m = re.match(r"^(nx[123])\s*=\s*(\d+)", ln)
    if m and m.group(1) not in chk:
        chk[m.group(1)] = int(m.group(2))
assert chk.get("nx1") == nx1 and chk.get("nx2") == nx2 and chk.get("nx3") == nx3, \
    "GRID MISMATCH: wrote %s, wanted %dx%dx%d" % (chk, nx1, nx2, nx3)
print("  %s  mesh %dx%dx%d mb=%d tlim=%.4f dt=%.5f chi=%g v=%.4f%s"
      % (out.split("/")[-2], nx1, nx2, nx3, mb, tlim, dt, chi, vwind,
         "  +cooling" if cool else ""))
