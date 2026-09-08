"""AREPO cloud-wind initial-condition generator.

Density: rho = rho_wind * [1 + (chi-1)/2 * (1-tanh((r/R-1)/0.1))].
Velocity: zero for r <= rv_scale*R; constant wind speed outside.
rv_scale defaults to 1.3. This is a sharp VELOCITY boundary, not a tanh.
Reference: Gronnow et al. (2018), section 2, https://arxiv.org/pdf/1805.03903 .
The paper supports this boundary prescription, not the former tanh velocity law.
Changing rv_scale moves the sharp boundary and cannot reproduce old tanh ICs.

This is a custom initializer for AREPO; AREPO evolves its own equations.
It does not establish identical boundary conditions or effective resolution
across codes. Equal-volume sampling matches initial lattice spacing only.
SPH and moving-mesh densities can differ from mass divided by lattice volume.
Use each run's parameter file and compile flags to establish boundary conditions.

Historical sources are preserved in CloudCrushing/audit_20260907/before/.
Existing IC files and completed simulation outputs have not been rewritten.
The writer refuses to overwrite an existing IC file.
Output format: Gadget-style HDF5 initial conditions.
Run this script with --help for its own supported arguments.
"""
import argparse
import numpy as np
import h5py

p = argparse.ArgumentParser()
p.add_argument('outdir', nargs='?', default='.')
p.add_argument('chi', nargs='?', type=float, default=10.0)
p.add_argument('ny', nargs='?', type=int, default=64)
p.add_argument('--ndim', type=int, choices=(2, 3), default=2,
               help='2 (default, unchanged legacy behaviour) or 3')
p.add_argument('--rv-scale', type=float, default=1.3, dest='rv_scale',
               help='velocity transition radius in units of R_cloud '
                    '(default 1.3; changes the sharp boundary, not historical tanh ICs)')
p.add_argument('--seed', type=int, default=42)
p.add_argument('--v-wind', type=float, default=2.582, dest='v_wind',
               help='wind velocity (default 2.582, the legacy hardcoded value, '
                    'kept so existing ICs regenerate bit-for-bit). The matched '
                    'campaign spec is 2*sqrt(5/3) = 2.581989, which the other '
                    'eleven codes compute exactly; pass --v-wind 2.581989 for '
                    'new production ICs.')
args = p.parse_args()

outdir = args.outdir
chi = args.chi
ny = args.ny
ndim = args.ndim
nx = 2 * ny
nz = ny if ndim == 3 else 1

FloatType = np.float64
IntType = np.int32

# geometry (code coordinates)
Boxsize = FloatType(10.0)        # y (and z) extent; x extent = LONG_X * Boxsize = 20
Lx, Ly, Lz = 20.0, 10.0, 10.0
cloud_x, cloud_y, cloud_z = 3.0, 5.0, 5.0   # cloud center: 3 from left edge, mid-plane
R_cloud = 1.0
dr_edge = 0.1

# physics
gamma = 5.0 / 3.0
rho_wind = 1.0
P0 = 1.0
v_wind = args.v_wind              # Mach 2.0 (cs = sqrt(gamma*P/rho) = 1.291)

# mesh-generating points on a uniform grid with a tiny deterministic jitter
# (avoids degenerate Voronoi construction on a perfectly regular lattice)
dx = Lx / nx
dy = Ly / ny
assert abs(dx - dy) < 1e-12
xc = (np.arange(nx) + 0.5) * dx
yc = (np.arange(ny) + 0.5) * dy

rng = np.random.default_rng(args.seed)

if ndim == 3:
    dz = Lz / nz
    assert abs(dx - dz) < 1e-12
    zc = (np.arange(nz) + 0.5) * dz
    X, Y, Z = np.meshgrid(xc, yc, zc, indexing='ij')
    x = X.ravel(); y = Y.ravel(); z = Z.ravel()
    N = x.size
    x += rng.uniform(-0.05, 0.05, N) * dx
    y += rng.uniform(-0.05, 0.05, N) * dy
    z += rng.uniform(-0.05, 0.05, N) * dz
    cell_volume = dx * dy * dz    # 3D: volume per cell
    r = np.sqrt((x - cloud_x) ** 2 + (y - cloud_y) ** 2 + (z - cloud_z) ** 2)
else:
    dz = 0.0
    X, Y = np.meshgrid(xc, yc, indexing='ij')
    x = X.ravel(); y = Y.ravel()
    N = x.size
    x += rng.uniform(-0.05, 0.05, N) * dx
    y += rng.uniform(-0.05, 0.05, N) * dy
    z = np.zeros(N, dtype=FloatType)
    cell_volume = dx * dy         # 2D: area per cell
    r = np.sqrt((x - cloud_x) ** 2 + (y - cloud_y) ** 2)

Pos = np.zeros((N, 3), dtype=FloatType)
Pos[:, 0] = x
Pos[:, 1] = y
Pos[:, 2] = z

# tanh cloud profile: density edge at R_cloud, velocity edge pushed out to RV*R_cloud
f = 0.5 * (1.0 - np.tanh((r - R_cloud) / dr_edge))
f_v = (r <= args.rv_scale * R_cloud).astype(float)
rho = rho_wind + (chi - 1.0) * f
vx = v_wind * (1.0 - f_v)

Mass = (rho * cell_volume).astype(FloatType)
Vel = np.zeros((N, 3), dtype=FloatType)
Vel[:, 0] = vx
Uthermal = (P0 / rho / (gamma - 1.0)).astype(FloatType)
Tracer = f.astype(FloatType).reshape(N, 1)   # passive scalar: cloud fraction

# write IC file; header modeled on examples/gresho_2d/create.py
with h5py.File(outdir + '/IC.hdf5', 'x') as IC:
    header = IC.create_group("Header")
    part0 = IC.create_group("PartType0")

    NumPart = np.array([N, 0, 0, 0, 0, 0], dtype=IntType)
    header.attrs.create("NumPart_ThisFile", NumPart)
    header.attrs.create("NumPart_Total", NumPart)
    header.attrs.create("NumPart_Total_HighWord", np.zeros(6, dtype=IntType))
    header.attrs.create("MassTable", np.zeros(6, dtype=IntType))
    header.attrs.create("Time", 0.0)
    header.attrs.create("Redshift", 0.0)
    header.attrs.create("BoxSize", Boxsize)
    header.attrs.create("NumFilesPerSnapshot", 1)
    header.attrs.create("Omega0", 0.0)
    header.attrs.create("OmegaB", 0.0)
    header.attrs.create("OmegaLambda", 0.0)
    header.attrs.create("HubbleParam", 1.0)
    header.attrs.create("Flag_Sfr", 0)
    header.attrs.create("Flag_Cooling", 0)
    header.attrs.create("Flag_StellarAge", 0)
    header.attrs.create("Flag_Metals", 0)
    header.attrs.create("Flag_Feedback", 0)
    header.attrs.create("Flag_DoublePrecision", 1 if Pos.dtype == np.float64 else 0)

    part0.create_dataset("ParticleIDs", data=np.arange(1, N + 1))
    part0.create_dataset("Coordinates", data=Pos)
    part0.create_dataset("Masses", data=Mass)
    part0.create_dataset("Velocities", data=Vel)
    part0.create_dataset("InternalEnergy", data=Uthermal)
    part0.create_dataset("PassiveScalars", data=Tracer)

t_cc = np.sqrt(chi) * R_cloud / v_wind
if ndim == 3:
    shape = "%dx%dx%d" % (nx, ny, nz)
else:
    shape = "%dx%d" % (nx, ny)
print("wrote %s/IC.hdf5: %dD, %d cells (%s), dx=%.5f, chi=%g, rv=%.2f, "
      "t_cc=%.4f, 5*t_cc=%.3f"
      % (outdir, ndim, N, shape, dx, chi, args.rv_scale, t_cc, 5 * t_cc))
print("  max rho=%.4f  max vx=%.4f  max(rho where vx>0.1*vwind)=%.4f"
      % (rho.max(), vx.max(), rho[vx > 0.1 * v_wind].max()))
