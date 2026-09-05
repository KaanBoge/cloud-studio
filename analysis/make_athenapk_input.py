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

if cool:
    # Townsend (2009) exact integration on a Schure et al. table, which is the
    # scheme AthenaPK already ships; only the parameter block was missing.
    if "<cooling>" not in text:
        text += (
            "\n<cooling>\n"
            "integrator = townsend\n"
            "table_filename = %s\n"
            "lambda_units_cgs = 1.0\n"
            "cfl = 0.1\n"
            "d_log_temp_tol = 1e-8\n"
            "d_e_tol = 1e-8\n"
            "max_iter = 100\n" % cool
        )
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
