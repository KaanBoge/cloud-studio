!!****if* source/Simulation/SimulationMain/CloudWind/Simulation_initBlock
!!
!! NAME
!!  Simulation_initBlock
!!
!! SYNOPSIS
!!  call Simulation_initBlock(real, pointer :: solnData(:,:,:,:),
!!                            type(Grid_tile_t) :: tileDesc)
!!
!! DESCRIPTION
!!  Initializes the cloud crushing problem ("cloud-wind matched setup"):
!!  a supersonic wind of density sim_rhoAmbient moving at sim_windVel in
!!  +x fills the domain, except for a dense cloud (radius sim_rCloud,
!!  density sim_rhoCloud) initially at rest, centered at
!!  (sim_xctr, sim_yctr, sim_zctr).  Pressure is uniform.
!!
!!  Density alone has a tanh edge with delta=sim_smoothWidth*sim_rCloud.
!!  sim_velocityIC selects sharp (0) or actual historical tanh (1)
!!  velocity at sim_rvScale*sim_rCloud (default 1.3). This is a custom
!!  controlled experiment, not a claim that a paper used tanh velocity.
!!  Neither prescription guarantees stability or no dense moving gas.
!!
!!  Density fraction:  f_rho(r) = 0.5*(1 - tanh((r - r_cl)/delta))
!!  Velocity fraction: f_v(r)   = 1 for r <= rvScale*r_cl, otherwise 0
!!  Density:           rho(r) = rho_wind + (rho_cloud - rho_wind)*f_rho(r)
!!  Velocity:          vx(r)  = v_wind * (1 - f_v(r))
!!
!!  Flash-X port of the FLASH 4.8 CloudCrush Simulation_initBlock
!!  (tileDesc-based API; verify against a shipped example such as Sedov
!!  after cloning, see staging README).
!!
!! ARGUMENTS
!!  solnData - pointer to the cell-centered solution data of the tile
!!  tileDesc - describes the tile (or block) to initialize
!!
!!***

!!REORDER(4): solnData

subroutine Simulation_initBlock(solnData, tileDesc)

  use Simulation_data, ONLY: sim_pAmbient, sim_rhoAmbient, sim_windVel, &
       sim_rhoCloud, sim_rCloud, sim_smoothWidth, sim_rvScale, sim_velocityIC, &
       sim_xCenter, sim_yCenter, sim_zCenter, &
       sim_gamma, sim_smallP, sim_smallT
  use Grid_tile, ONLY : Grid_tile_t
  use Grid_interface, ONLY : Grid_getCellCoords

  implicit none

#include "constants.h"
#include "Simulation.h"

  real, dimension(:,:,:,:), pointer :: solnData
  type(Grid_tile_t), intent(in) :: tileDesc

  integer :: i, j, k
  integer, dimension(MDIM) :: lo, hi
  real, allocatable, dimension(:) :: xCoord, yCoord, zCoord
  real :: xDist, yDist, zDist, radius, delta, cloudFrac, velFrac
  real :: rho, p, vx, eint, ener

  lo(:) = tileDesc%blkLimitsGC(LOW, :)
  hi(:) = tileDesc%blkLimitsGC(HIGH, :)

  allocate(xCoord(lo(IAXIS):hi(IAXIS)));  xCoord = 0.0
  allocate(yCoord(lo(JAXIS):hi(JAXIS)));  yCoord = 0.0
  allocate(zCoord(lo(KAXIS):hi(KAXIS)));  zCoord = 0.0

  call Grid_getCellCoords(IAXIS, CENTER, tileDesc%level, lo, hi, xCoord)
#if NDIM > 1
  call Grid_getCellCoords(JAXIS, CENTER, tileDesc%level, lo, hi, yCoord)
#endif
#if NDIM > 2
  call Grid_getCellCoords(KAXIS, CENTER, tileDesc%level, lo, hi, zCoord)
#endif

  ! width of the smoothed cloud edge; avoid division by zero for sharp edge
  delta = max(sim_smoothWidth * sim_rCloud, tiny(1.0))

  do k = lo(KAXIS), hi(KAXIS)
     zDist = 0.0
#if NDIM > 2
     zDist = zCoord(k) - sim_zCenter
#endif
     do j = lo(JAXIS), hi(JAXIS)
        yDist = 0.0
#if NDIM > 1
        yDist = yCoord(j) - sim_yCenter
#endif
        do i = lo(IAXIS), hi(IAXIS)
           xDist = xCoord(i) - sim_xCenter

           radius = sqrt(xDist**2 + yDist**2 + zDist**2)

           ! density edge: 1 deep inside the cloud, 0 far outside
           cloudFrac = 0.5 * (1.0 - tanh((radius - sim_rCloud)/delta))

           ! Only the velocity prescription varies within the pair.
           if (sim_velocityIC == 1) then
              velFrac = 0.5 * (1.0 - tanh((radius - sim_rvScale*sim_rCloud)/delta))
           else
              velFrac = 0.0
              if (radius <= sim_rvScale*sim_rCloud) velFrac = 1.0
           endif

           rho = sim_rhoAmbient + (sim_rhoCloud - sim_rhoAmbient) * cloudFrac
           vx  = sim_windVel * (1.0 - velFrac)

           p    = max(sim_pAmbient, sim_smallP)
           eint = p / ((sim_gamma - 1.0) * rho)
           ener = eint + 0.5 * vx**2

           solnData(DENS_VAR, i, j, k) = rho
           solnData(PRES_VAR, i, j, k) = p
           solnData(VELX_VAR, i, j, k) = vx
           solnData(VELY_VAR, i, j, k) = 0.0
           solnData(VELZ_VAR, i, j, k) = 0.0
           solnData(ENER_VAR, i, j, k) = ener
#ifdef EINT_VAR
           solnData(EINT_VAR, i, j, k) = eint
#endif
#ifdef GAME_VAR
           solnData(GAME_VAR, i, j, k) = sim_gamma
#endif
#ifdef GAMC_VAR
           solnData(GAMC_VAR, i, j, k) = sim_gamma
#endif
#ifdef TEMP_VAR
           solnData(TEMP_VAR, i, j, k) = sim_smallT
#endif
        enddo
     enddo
  enddo

  deallocate(xCoord)
  deallocate(yCoord)
  deallocate(zCoord)

end subroutine Simulation_initBlock
