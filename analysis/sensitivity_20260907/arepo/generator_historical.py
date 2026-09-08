"""Create AREPO HDF5 initial conditions for the 2D/3D cloud-crushing test.

Cloud-wind matched setup (identical physics across codes):
  ambient/wind: rho=1, P=1, vx = 2.582 (Mach 2, cs=1.291), gamma=5/3
  cloud: overdensity chi, static, P=1, radius 1.0 (circle in 2D, sphere in 3D)
  density edge:  f   = 0.5*(1 - tanh((r - 1.0)/0.1));  rho = 1 + (chi-1)*f
  velocity edge: f_v = 0.5*(1 - tanh((r - RV*1.0)/0.1)); vx = 2.582*(1 - f_v)

RV (--rv-scale) defaults to 1.3: the velocity transition is deliberately placed
OUTSIDE the dense edge so that no cell is simultaneously dense and fast.  Cells
that are both dense and fast produce catastrophic cancellation between kinetic
and total energy and poison the early evolution.  This matches the convention in
gasoline/ics/make_gasoline_cloudwind.py (RV_SCALE = 1.3) and in the Athena++
problem generator CloudCrushing/A8/cloud_wind.c.

  NOTE ON REPRODUCIBILITY: the archived 2D ICs in runs/AREPO2D_chi10 and
  runs/AREPO2D_chi100 were written by the earlier version of this script, which
  used the co-located form vx = 2.582*(1 - f).  Those IC.hdf5 files are
  untouched.  To regenerate them bit-for-bit, pass --rv-scale 1.0.

Periodic long-box variant (Braspenning+2023 style), as appropriate for a
moving-mesh code: box 20 x 10 (x 10 in 3D), code coords x in [0,20],
y in [0,10], z in [0,10], i.e. x in [-3,17] and y,z in [-5,5] in cloud radii.
Cloud centered 3 units from the left edge at (3, 5) / (3, 5, 5).
AREPO compile-time: BoxSize=10 with LONG_X=2.0 gives the 20 x 10 (x 10) box.
The streamwise x axis stays periodic (the wind supply must not be cut off);
the transverse faces are outflow via REFLECTIVE_Y=2 (and REFLECTIVE_Z=2 in 3D).

Header structure copied from examples/gresho_2d/create.py (Rainer Weinberger).

Usage: python make_ic_cloud.py <output_dir> [chi] [ny] [--ndim {2,3}] [--rv-scale RV]
  chi: cloud overdensity (default 10)
  ny : mesh-generating points across the y extent (10 units).
       nx = 2*ny, and in 3D nz = ny.
       2D default 64 (128x64 = 8192 cells, smoke test); production 256+.
       3D: ny=100 gives 200x100x100 = 2.0e6 cells (dx = 0.1, 10 cells per
       cloud radius); ny=128 gives 256x128x128 = 4.2e6 cells (dx = 0.078).
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
                    '(default 1.3; use 1.0 to reproduce the legacy 2D ICs)')
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
f_v = 0.5 * (1.0 - np.tanh((r - args.rv_scale * R_cloud) / dr_edge))
rho = rho_wind + (chi - 1.0) * f
vx = v_wind * (1.0 - f_v)

Mass = (rho * cell_volume).astype(FloatType)
Vel = np.zeros((N, 3), dtype=FloatType)
Vel[:, 0] = vx
Uthermal = (P0 / rho / (gamma - 1.0)).astype(FloatType)
Tracer = f.astype(FloatType).reshape(N, 1)   # passive scalar: cloud fraction

# write IC file; header modeled on examples/gresho_2d/create.py
with h5py.File(outdir + '/IC.hdf5', 'w') as IC:
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
