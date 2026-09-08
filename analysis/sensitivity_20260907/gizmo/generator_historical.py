#!/usr/bin/env python3
"""
Cloud-wind matched setup IC generator for GIZMO (Gadget-format HDF5).
Modeled on gizmo-public/scripts/make_IC.py.

Physics (identical across all codes in the comparison):
  ambient/wind: rho=1, P=1, vx=2.582 (Mach 2, cs=1.291), gamma=5/3
  cloud: overdensity chi, static, P=1, radius 1, centered at origin
  density edge:  f   = 0.5*(1 - tanh((r - 1.0)/0.1));    rho = 1 + (chi-1)*f
  velocity edge: f_v = 0.5*(1 - tanh((r - RV*1.0)/0.1)); vx  = 2.582*(1 - f_v)

RV (--rv-scale) defaults to 1.3: the velocity transition is deliberately placed
OUTSIDE the dense edge so that no particle is simultaneously dense and fast.
Particles that are both dense and fast produce catastrophic cancellation between
kinetic and total energy and poison the early evolution.  This matches
arepo/runs/make_ic_cloud.py (--rv-scale 1.3), gasoline/ics/make_gasoline_cloudwind.py
(RV_SCALE = 1.3) and the Athena++ problem generator CloudCrushing/A8/cloud_wind.c.

  CAVEAT (measured 2026-08-26): rv_scale=1.3 delivers its stated property only at
  chi=10.  The max density among material moving faster than 0.1*v_wind is 1.20 at
  chi=10, 3.16 at chi=100 and 22.8 at chi=1000 -- this is the tanh tail, not a
  sampling artifact, and it is identical in every code in the campaign.  It is
  kept at 1.3 anyway because eight grid runs at chi=100/1000 are already finished
  with 1.3 and consistency with them dominates.

  NOTE ON REPRODUCIBILITY: the archived 2D ICs under runs/GIZMO2D_chi10_mfm and
  runs/GIZMO2D_chi10_mfv were written by the earlier version of this script,
  which used the co-located form vx = 2.582*(1 - f).  Those .hdf5 files are
  untouched.  To regenerate them bit-for-bit, pass --rv-scale 1.0.
  domain: x in [-3,17], y in [-5,5] (2D); +z in [-5,5] (3D)

GIZMO variant: long box (Braspenning+2023 style).  Coordinates are shifted so the
box is [0,20]x[0,10]x[0,10] (BoxSize=10, BOX_LONG_X=2); cloud center -> (3,5,5).
x stays periodic (GIZMO has no wind injector); the transverse faces are OUTFLOW
via BOX_OUTFLOW_Y / BOX_OUTFLOW_Z in Config_MFM_3D.sh and Config_MFV_3D.sh.

SAMPLING CONVENTION (--mass-mode), settled 2026-08-26 for the twelve-code
campaign:

  volume  EQUAL VOLUME / variable mass.  THE LADDER CONVENTION.  A single
          regular lattice of spacing dx covers the whole box; every particle
          carries m = rho(r)*dx^ndims and u = P0/((gamma-1)*rho(r)).  N is
          independent of chi, the spatial resolution equals the grid codes'
          cell size at EVERY radius, and P = P0 holds exactly everywhere by
          construction.  Identical in spirit to arepo/runs/make_ic_cloud.py
          (Mass = rho*cell_volume) and gadget4/ics/make_g4_cloudwind.py
          (mass = rho*dx**dim).

  equal   EQUAL MASS / chi-refined cloud.  LEGACY, and the SPH-literature
          default (Agertz+2007, Hopkins 2015, Braspenning+2023).  Kept as the
          module default so every existing call site and every archived IC
          reproduces bit-for-bit.  Use it only for an explicitly-labelled
          equal-mass control set, never for a ladder rung: it resolves the
          cloud interior chi^(1/3) times finer than the wind (and than the grid
          codes at the same rung), it makes N a function of chi, and the
          r<=1.4 sampling seam puts a pressure dip of 0.3% / 3.2% / 25% at
          chi = 10 / 100 / 1000 into the cloud's near wake.

Usage: python3 make_cloudwind_ic.py --chi 10 --dx 0.05 --ndims 2 --fname ics.hdf5
       python3 make_cloudwind_ic.py --chi 1000 --level 5 --ndims 3 \
               --mass-mode volume --fname ics.hdf5
"""
import argparse
import numpy as np
import h5py

def rho_profile(r, chi):
    f = 0.5 * (1.0 - np.tanh((r - 1.0) / 0.1))
    return 1.0 + (chi - 1.0) * f, f

def vel_profile(r, vwind, rv_scale=1.3):
    """Velocity edge, pushed out to rv_scale*R_cloud so no particle is both
    dense and fast (see module docstring)."""
    f_v = 0.5 * (1.0 - np.tanh((r - rv_scale * 1.0) / 0.1))
    return vwind * (1.0 - f_v)


def _write(fname, pos, vel, ids, m, u, N):
    """Gadget/HDF5 type-3 writer, shared by both sampling modes."""
    with h5py.File(fname, 'w') as fh:
        npart = np.array([N, 0, 0, 0, 0, 0])
        h = fh.create_group('Header')
        h.attrs['NumPart_ThisFile'] = npart
        h.attrs['NumPart_Total'] = npart
        h.attrs['NumPart_Total_HighWord'] = 0 * npart
        h.attrs['MassTable'] = np.zeros(6)
        h.attrs['Time'] = 0.0
        h.attrs['Redshift'] = 0.0
        h.attrs['BoxSize'] = 10.0
        h.attrs['NumFilesPerSnapshot'] = 1
        h.attrs['Flag_DoublePrecision'] = 0  # datasets stored float32 (code default)
        h.attrs['Flag_Sfr'] = 0; h.attrs['Flag_Cooling'] = 0
        h.attrs['Flag_StellarAge'] = 0; h.attrs['Flag_Metals'] = 0
        h.attrs['Flag_Feedback'] = 0
        h.attrs['Omega0'] = 0.0; h.attrs['OmegaLambda'] = 0.0
        h.attrs['HubbleParam'] = 1.0
        p = fh.create_group('PartType0')
        p.create_dataset('Coordinates', data=pos.astype(np.float32))
        p.create_dataset('Velocities', data=vel.astype(np.float32))
        p.create_dataset('ParticleIDs', data=ids)
        p.create_dataset('Masses', data=m.astype(np.float32))
        p.create_dataset('InternalEnergy', data=u.astype(np.float32))


def _make_ic_equal_volume(chi, dx, ndims, fname, gamma, vwind, rv_scale,
                          Lx, Ly, xc, yc):
    """One regular lattice over the whole box; m = rho*dx^ndims."""
    nx = int(round(Lx / dx)); ny = int(round(Ly / dx))
    dxx, dyy = Lx / nx, Ly / ny
    x1 = (np.arange(nx) + 0.5) * dxx
    y1 = (np.arange(ny) + 0.5) * dyy
    if ndims == 2:
        X, Y = np.meshgrid(x1, y1, indexing='ij')
        x = X.ravel(); y = Y.ravel(); z = np.zeros_like(x)
        del X, Y
        r = np.sqrt((x - xc) ** 2 + (y - yc) ** 2)
        cell = dxx * dyy
        shape = (nx, ny)
    else:
        Lz, zc = 10.0, 10.0 / 2.0
        nz = int(round(Lz / dx)); dzz = Lz / nz
        z1 = (np.arange(nz) + 0.5) * dzz
        X, Y, Z = np.meshgrid(x1, y1, z1, indexing='ij')
        x = X.ravel(); y = Y.ravel(); z = Z.ravel()
        del X, Y, Z
        r = np.sqrt((x - xc) ** 2 + (y - yc) ** 2 + (z - zc) ** 2)
        cell = dxx * dyy * dzz
        shape = (nx, ny, nz)
    N = x.size

    rho, f = rho_profile(r, chi)
    vx = vel_profile(r, vwind, rv_scale)
    u = 1.0 / ((gamma - 1.0) * rho)   # P = 1 everywhere, exactly
    m = rho * cell                     # VARIABLE mass, EQUAL volume

    # cloud tracer by ID: f >= 0.5 (r <= R_cloud) -> IDs 1..Nc, ambient -> Nc+1..N.
    # Same cloud criterion as gadget4/ics/make_g4_cloudwind.py.
    cloud = f >= 0.5
    Nc = int(cloud.sum())
    ids = np.empty(N, dtype=np.uint32)
    ids[cloud] = np.arange(1, Nc + 1, dtype=np.uint32)
    ids[~cloud] = np.arange(Nc + 1, N + 1, dtype=np.uint32)

    pos = np.zeros((N, 3)); pos[:, 0] = x; pos[:, 1] = y; pos[:, 2] = z
    vel = np.zeros((N, 3)); vel[:, 0] = vx
    _write(fname, pos, vel, ids, m, u, N)

    P = (gamma - 1.0) * rho * u
    dense_fast = rho[vx > 0.1 * vwind].max() if np.any(vx > 0.1 * vwind) else 0.0
    tcc = np.sqrt(chi) * 1.0 / vwind
    vol = Lx * Ly if ndims == 2 else Lx * Ly * 10.0
    excess = (chi - 1.0) * ((4.0 / 3.0) * np.pi if ndims == 3 else np.pi)
    print('mass-mode=volume  (EQUAL VOLUME, variable mass)')
    print(f'grid {shape}  dx={dxx:.9f}  cell={cell:.9e}  '
          f'{1.0/dxx:.2f} elements per cloud radius')
    print(f'wrote {fname}: N={N}  (cloud f>=0.5: Nc={Nc}, IDs 1..{Nc})')
    print(f'  m  : min={m.min():.6e} max={m.max():.6e} ratio={m.max()/m.min():.2f}')
    print(f'  rho: min={rho.min():.8f} max={rho.max():.6f}')
    print(f'  P  : min={P.min():.10f} max={P.max():.10f}  (must both be 1)')
    print(f'  rv_scale={rv_scale}: max rho among vx>0.1*vwind = {dense_fast:.4f}')
    print(f'chi={chi}  vwind={vwind:.6f}  t_cc={tcc:.6f}  5*t_cc={5*tcc:.6f}')
    print(f'total mass={m.sum():.5f}  (uniform box {vol:.1f} + analytic cloud '
          f'excess {excess:.5f} = {vol + excess:.5f})')


def make_ic(chi=10.0, dx=0.05, ndims=2, fname='ics.hdf5', seed=42,
            mach=2.0, gamma=5.0/3.0, rv_scale=1.3, mass_mode='equal'):
    if mass_mode not in ('equal', 'volume'):
        raise ValueError("mass_mode must be 'equal' or 'volume'")
    rng = np.random.default_rng(seed)
    cs_amb = np.sqrt(gamma * 1.0 / 1.0)          # = 1.291
    vwind = mach * cs_amb                         # = 2.581989
    # box: x [-3,17] -> [0,20]; y [-5,5] -> [0,10]; (z same as y in 3D)
    Lx, Ly = 20.0, 10.0
    xc, yc = 3.0, 5.0                             # cloud center after shift
    r_cut = 1.4                                   # f(1.4)=1.7e-4: edge of cloud sampling region

    if mass_mode == 'volume':
        return _make_ic_equal_volume(chi, dx, ndims, fname, gamma, vwind,
                                     rv_scale, Lx, Ly, xc, yc)

    # --- ambient regular lattice (exact periodic tiling) ---
    nx = int(round(Lx / dx)); ny = int(round(Ly / dx))
    dxx, dyy = Lx / nx, Ly / ny
    x1 = (np.arange(nx) + 0.5) * dxx
    y1 = (np.arange(ny) + 0.5) * dyy
    if ndims == 2:
        xa, ya = np.meshgrid(x1, y1, indexing='ij')
        xa = xa.ravel(); ya = ya.ravel(); za = np.zeros_like(xa)
        ra = np.sqrt((xa - xc)**2 + (ya - yc)**2)
        mpart = 1.0 * dxx * dyy
    else:
        Lz, zc = 10.0, 5.0
        nz = int(round(Lz / dx)); dzz = Lz / nz
        z1 = (np.arange(nz) + 0.5) * dzz
        xa, ya, za = np.meshgrid(x1, y1, z1, indexing='ij')
        xa = xa.ravel(); ya = ya.ravel(); za = za.ravel()
        ra = np.sqrt((xa - xc)**2 + (ya - yc)**2 + (za - zc)**2)
        mpart = 1.0 * dxx * dyy * dzz
    keep = ra > r_cut
    xa, ya, za = xa[keep], ya[keep], za[keep]

    # --- cloud region: fine lattice, acceptance p = rho/(chi) ---
    dxf = dx / chi**(1.0 / ndims)
    nf = int(np.ceil(2 * r_cut / dxf))
    g1 = (np.arange(nf) + 0.5) * dxf - r_cut
    if ndims == 2:
        xf, yf = np.meshgrid(g1, g1, indexing='ij')
        xf = xf.ravel(); yf = yf.ravel(); zf = np.zeros_like(xf)
        rf = np.sqrt(xf**2 + yf**2)
    else:
        xf, yf, zf = np.meshgrid(g1, g1, g1, indexing='ij')
        xf = xf.ravel(); yf = yf.ravel(); zf = zf.ravel()
        rf = np.sqrt(xf**2 + yf**2 + zf**2)
    inside = rf <= r_cut
    xf, yf, zf, rf = xf[inside], yf[inside], zf[inside], rf[inside]
    rho_f, _ = rho_profile(rf, chi)
    accept = rng.random(rf.size) < (rho_f / chi)
    xf, yf, zf, rf = xf[accept], yf[accept], zf[accept], rf[accept]
    xf = xf + xc; yf = yf + yc
    if ndims == 3:
        zf = zf + zc

    # --- combine: cloud-region particles FIRST so IDs 1..Ncloud tag cloud material ---
    Nc = xf.size
    x = np.concatenate([xf, xa]); y = np.concatenate([yf, ya]); z = np.concatenate([zf, za])
    N = x.size
    if ndims == 2:
        r = np.sqrt((x - xc)**2 + (y - yc)**2)
    else:
        r = np.sqrt((x - xc)**2 + (y - yc)**2 + (z - zc)**2)
    rho, f = rho_profile(r, chi)
    vx = vel_profile(r, vwind, rv_scale)
    u = 1.0 / ((gamma - 1.0) * rho)   # P=1 everywhere
    m = np.full(N, mpart)
    ids = np.arange(1, N + 1, dtype=np.uint32)

    pos = np.zeros((N, 3)); pos[:, 0] = x; pos[:, 1] = y; pos[:, 2] = z
    vel = np.zeros((N, 3)); vel[:, 0] = vx

    _write(fname, pos, vel, ids, m, u, N)

    dense_fast = rho[vx > 0.1 * vwind].max() if np.any(vx > 0.1 * vwind) else 0.0
    print(f'rv_scale={rv_scale}: max rho among particles with vx>0.1*vwind = '
          f'{dense_fast:.4f} (should be ~1 for rv_scale=1.3)')
    tcc = np.sqrt(chi) * 1.0 / vwind
    print(f'wrote {fname}: N={N} (cloud-region={Nc}, ambient={N-Nc}), '
          f'mpart={mpart:.4e}, dx_amb={dxx:.4f}, dx_cloud={dxf:.4f}')
    print(f'chi={chi}, vwind={vwind:.4f}, t_cc={tcc:.4f}, 5 t_cc={5*tcc:.3f}')
    print(f'total mass={m.sum():.3f} (analytic ambient-only would be {1.0*Lx*Ly if ndims==2 else 1.0*Lx*Ly*10.0:.1f})')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--chi', type=float, default=10.0)
    ap.add_argument('--dx', type=float, default=0.05, help='ambient inter-particle spacing')
    ap.add_argument('--ndims', type=int, default=2, choices=[2, 3])
    ap.add_argument('--fname', default='ics.hdf5')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--rv-scale', type=float, default=1.3, dest='rv_scale',
                    help='velocity transition radius in units of R_cloud '
                         '(default 1.3; use 1.0 to reproduce the legacy 2D ICs)')
    ap.add_argument('--mass-mode', default='equal', choices=['equal', 'volume'],
                    dest='mass_mode',
                    help='equal = equal-mass with a chi-refined cloud (legacy '
                         'default, preserves every archived IC); volume = '
                         'equal-volume variable-mass lattice (the ladder convention)')
    ap.add_argument('--level', type=int, default=None,
                    help='shared ladder level: nx = 8*2^level across the 20-long '
                         'box, so dx = 20/nx.  level 3 -> 64x32x32 (3.2 elements '
                         'per cloud radius), 4 -> 128x64x64 (6.4), 5 -> '
                         '256x128x128 (12.8).  Overrides --dx.')
    a = ap.parse_args()
    dx = a.dx
    if a.level is not None:
        nx = 8 * (2 ** a.level)
        dx = 20.0 / nx
        print(f'--level {a.level}: nx={nx}  dx={dx:.9f}  '
              f'{1.0/dx:.2f} elements per cloud radius')
    make_ic(chi=a.chi, dx=dx, ndims=a.ndims, fname=a.fname, seed=a.seed,
            rv_scale=a.rv_scale, mass_mode=a.mass_mode)
