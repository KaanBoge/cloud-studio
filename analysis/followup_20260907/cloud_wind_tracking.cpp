//========================================================================================
// Athena++ astrophysical MHD code
// Copyright(C) 2014 James M. Stone <jmstone@princeton.edu> and other code contributors
// Licensed under the 3-clause BSD License, see LICENSE file for details
//========================================================================================
//! \file cloud_wind_tracking.cpp
//! \brief Experimental, restart-safe density-centroid frame tracking.
//! Not the complete Farber & Gronke upstream-buffer scheme. Not production-certified.
//! \brief Cloud-wind ("wind tunnel") problem generator, matched to the multi-code
//!  cloud-crushing comparison setup (FLASH CloudCrush / Athena4.2 cloud_wind.c port).
//!
//!  A uniform Mach-M wind (rho=1, P=1, vx = Mach*c_s flowing +x1) streams past a
//!  static spherical cloud of overdensity drat (chi) in exact pressure equilibrium.
//!  Cloud radius fixed at 1.0, centered at the origin. Density uses a tanh
//!  edge; velocity has a sharp boundary at rv_scale times the cloud radius:
//!     f  = 0.5*(1 - tanh((r - 1.0)/0.1))
//!     rho = 1 + (chi - 1)*f
//!     f_v = 1 inside r < rv_scale*1.0, 0 outside (SHARP top-hat,
//!           per Gronnow+2018); rv_scale default 1.3
//!     vx  = v_wind*(1 - f_v)
//!  Suggested domain: x1 in [-3,17], x2 in [-5,5] (x3 in [-5,5] for 3D).
//!  Input parameters:
//!    - problem/Mach = wind Mach number (v_wind / c_s,ambient)
//!    - problem/drat = cloud/ambient density ratio (chi)
//!  Cloud material is labeled with passive scalar r(0) = f when NSCALARS > 0.
//!  Inner-x1 boundary must be set to "user" in the input file: it holds the
//!  fixed wind state (inflow BC).
//========================================================================================

// C headers

// C++ headers
#include <cmath>      // sqrt(), tanh()
#include <iostream>   // endl
#include <sstream>    // stringstream
#include <stdexcept>  // runtime_error
#include <string>     // c_str()

// Athena++ headers
#include "../athena.hpp"
#include "../athena_arrays.hpp"
#include "../bvals/bvals.hpp"
#include "../coordinates/coordinates.hpp"
#include "../eos/eos.hpp"
#include "../field/field.hpp"
#include "../hydro/hydro.hpp"
#include "../mesh/mesh.hpp"
#include "../parameter_input.hpp"
#include "../scalars/scalars.hpp"
#ifdef MPI_PARALLEL
#include <mpi.h>
#endif

// wind state, shared with the inner-x1 boundary function
namespace {
Real gmma1, dl, pl, ul;
Real chi_track;
bool tracking_on;
} // namespace

Real TrackingHistory(MeshBlock *pmb, int index) {
  return pmb->pmy_mesh->ruser_mesh_data[0](index);
}

// fixes BCs on L-x1 (left edge) of grid to the wind state (inflow)
void CloudWindInnerX1(MeshBlock *pmb, Coordinates *pco, AthenaArray<Real> &prim,
                      FaceField &b, Real time, Real dt,
                      int il, int iu, int jl, int ju, int kl, int ku, int ngh);

//========================================================================================
//! \fn void Mesh::InitUserMeshData(ParameterInput *pin)
//  \brief Enroll the user inflow boundary on inner-x1.
//========================================================================================

void Mesh::InitUserMeshData(ParameterInput *pin) {
  // ProblemGenerator is NOT invoked when reading a checkpoint: all constants
  // needed by boundary callbacks must be initialized here as well as at t=0.
  const Real gamma = pin->GetReal("hydro", "gamma");
  gmma1 = gamma - 1.0;
  dl = pl = 1.0;
  ul = pin->GetReal("problem", "Mach") * std::sqrt(gamma);
  chi_track = pin->GetReal("problem", "drat");
  tracking_on = pin->GetOrAddBoolean("problem", "galilean_shift", false);
  AllocateRealUserMeshDataField(1);
  ruser_mesh_data[0].NewAthenaArray(2);
  ruser_mesh_data[0](0) = 0.0;  // cumulative frame velocity
  ruser_mesh_data[0](1) = 0.0;  // frame displacement in the original lab frame
  // Athena++ restores these allocated arrays from a NEW-format checkpoint
  // immediately after this callback. Never restart an old binary's checkpoint.
  AllocateUserHistoryOutput(2);
  EnrollUserHistoryOutput(0, TrackingHistory, "frame_v", UserHistoryOperation::max);
  EnrollUserHistoryOutput(1, TrackingHistory, "frame_x", UserHistoryOperation::max);
  EnrollUserBoundaryFunction(BoundaryFace::inner_x1, CloudWindInnerX1);
  return;
}

//========================================================================================
//! \fn void MeshBlock::ProblemGenerator(ParameterInput *pin)
//  \brief Problem Generator for the cloud-wind (wind tunnel) problem
//========================================================================================

void MeshBlock::ProblemGenerator(ParameterInput *pin) {
  Real gmma  = peos->GetGamma();
  gmma1 = gmma - 1.0;

  // Read input parameters
  Real rad  = 1.0;         // cloud radius, fixed
  Real edge = 0.1*rad;     // tanh smoothing width, matches FLASH
  Real mach = pin->GetReal("problem","Mach");
  Real drat = pin->GetReal("problem","drat");
  // Velocity transition radius in units of the cloud radius.  The adopted
  // prescription sets zero velocity through rv_scale*R and constant wind
  // speed outside (Gronnow et al. 2018, section 2). rv_scale moves this
  // boundary; it does not restore the historical tanh velocity law.
  Real rvs  = pin->GetOrAddReal("problem","rv_scale",1.3);

  if (MAGNETIC_FIELDS_ENABLED) {
    std::stringstream msg;
    msg << "### FATAL ERROR in cloud_wind.cpp ProblemGenerator" << std::endl
        << "This comparison setup is pure hydro; configure without -b" << std::endl;
    ATHENA_ERROR(msg);
  }

  // Ambient (wind) state: rho=1, P=1 so c_s = sqrt(gamma) ~ 1.291, as in FLASH
  Real dr = 1.0;
  Real pr = 1.0;

  // Wind state shared with the boundary function
  dl = dr;
  pl = pr;
  ul = mach*std::sqrt(gmma*pr/dr);

  // Initialize the grid: wind everywhere, static smoothed cloud at the origin
  for (int k=ks; k<=ke; k++) {
    for (int j=js; j<=je; j++) {
      for (int i=is; i<=ie; i++) {
        Real diag = std::sqrt(SQR(pcoord->x1v(i)) + SQR(pcoord->x2v(j))
                              + SQR(pcoord->x3v(k)));
        Real f  = 0.5*(1.0 - std::tanh((diag - rad)/edge));
        Real d  = dr*(1.0 + (drat - 1.0)*f);
        // Sharp top-hat, NOT tanh. Gronnow, Tepper-Garcia &
        // Bland-Hawthorn (2018) sec. 2: "The velocity and metallicity
        // follow sharp top-hat profiles, with boundaries at r = 1.3 r_c".
        // The density keeps its tanh; only the velocity is a step.
        // The constant outer value is velocity, not momentum density.
        Real fv = (diag > rvs*rad) ? 0.0 : 1.0;
        Real vx = ul*(1.0 - fv);

        phydro->u(IDN,k,j,i) = d;
        phydro->u(IM1,k,j,i) = d*vx;
        phydro->u(IM2,k,j,i) = 0.0;
        phydro->u(IM3,k,j,i) = 0.0;
        phydro->u(IEN,k,j,i) = pr/gmma1 + 0.5*d*vx*vx;

        // passive scalar tracer of cloud material: concentration r = f
        if (NSCALARS > 0) {
          for (int n=0; n<NSCALARS; ++n) {
            pscalars->s(n,k,j,i) = d*f;
          }
        }
      }
    }
  }
  return;
}

//----------------------------------------------------------------------------------------
//! \fn void CloudWindInnerX1()
//  \brief Inflow boundary on inner-x1: ghost zones held fixed at the wind state.

void CloudWindInnerX1(MeshBlock *pmb, Coordinates *pco, AthenaArray<Real> &prim,
                      FaceField &b, Real time, Real dt,
                      int il, int iu, int jl, int ju, int kl, int ku, int ngh) {
  for (int k=kl; k<=ku; ++k) {
    for (int j=jl; j<=ju; ++j) {
      for (int i=1; i<=ngh; ++i) {
        prim(IDN,k,j,il-i) = dl;
        prim(IVX,k,j,il-i) = ul - pmb->pmy_mesh->ruser_mesh_data[0](0);
        prim(IVY,k,j,il-i) = 0.0;
        prim(IVZ,k,j,il-i) = 0.0;
        prim(IPR,k,j,il-i) = pl;
      }
    }
  }
  // pure wind carries no cloud material
  if (NSCALARS > 0) {
    for (int n=0; n<NSCALARS; ++n) {
      for (int k=kl; k<=ku; ++k) {
        for (int j=jl; j<=ju; ++j) {
          for (int i=1; i<=ngh; ++i) {
            pmb->pscalars->r(n,k,j,il-i) = 0.0;
            pmb->pscalars->s(n,k,j,il-i) = 0.0;
          }
        }
      }
    }
  }
}

// Applied once per completed step, before NewTimeStep and snapshot output.
// Algebraic momentum/energy transformation preserves internal energy. Discrete
// grid evolution is not claimed to be exactly Galilean invariant.
void Mesh::UserWorkInLoop() {
  Real &boost = ruser_mesh_data[0](0);
  Real &offset = ruser_mesh_data[0](1);
  offset += boost * dt;  // frame used while taking the step just completed
  if (!tracking_on) return;
  Real sums[2] = {0.0, 0.0};
  for (int b=0; b<nblocal; ++b) {
    MeshBlock *mb = my_blocks(b);
    auto &u = mb->phydro->u;
    for (int k=mb->ks; k<=mb->ke; ++k)
      for (int j=mb->js; j<=mb->je; ++j)
        for (int i=mb->is; i<=mb->ie; ++i) {
          if (u(IDN,k,j,i) <= chi_track/3.0) continue;
          const Real volume = mb->pcoord->GetCellVolume(k,j,i);
          sums[0] += u(IDN,k,j,i)*volume;
          sums[1] += u(IM1,k,j,i)*volume;
        }
  }
#ifdef MPI_PARALLEL
  MPI_Allreduce(MPI_IN_PLACE, sums, 2, MPI_ATHENA_REAL, MPI_SUM, MPI_COMM_WORLD);
#endif
  if (sums[0] <= 0.0) return;
  const Real dv = sums[1]/sums[0];
  if (!std::isfinite(dv)) {
    std::stringstream msg; msg << "Nonfinite frame velocity"; ATHENA_ERROR(msg);
  }
  if (dv == 0.0) return;
  // The fixed upstream boundary is not an upstream material-preserving buffer.
  // Refuse a reversed inflow rather than silently change the experiment.
  if (boost+dv >= ul) {
    std::stringstream msg; msg << "Tracking would reverse wind inflow; buffer scheme required";
    ATHENA_ERROR(msg);
  }
  boost += dv;
  for (int b=0; b<nblocal; ++b) {
    MeshBlock *mb = my_blocks(b);
    auto &u = mb->phydro->u;
    auto &w = mb->phydro->w;
    // Ghost primitives participate in reconstruction at the start of the next
    // step. Shift them too; otherwise an uninterrupted run keeps old-frame
    // ghosts while a checkpoint restart regenerates new-frame ghosts.
    for (int k=0; k<mb->ncells3; ++k)
      for (int j=0; j<mb->ncells2; ++j)
        for (int i=0; i<mb->ncells1; ++i) {
          const Real rho=u(IDN,k,j,i), momentum=u(IM1,k,j,i);
          u(IM1,k,j,i) = momentum-rho*dv;
          u(IEN,k,j,i) += -momentum*dv+0.5*rho*dv*dv;
          // Primitive output and the next CFL estimate must see this frame too.
          w(IVX,k,j,i) -= dv;
        }
    mb->phydro->NewBlockTimeStep();
  }
}
