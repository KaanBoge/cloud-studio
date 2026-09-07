!!****if* source/Simulation/SimulationMain/CloudCrush/Simulation_init
!!
!! NAME
!!  Simulation_init
!!
!! SYNOPSIS
!!  call Simulation_init()
!!
!! DESCRIPTION
!!  Reads the runtime parameters for the CloudCrush problem.
!!
!!***

subroutine Simulation_init()

  use Simulation_data
  use Driver_interface, ONLY : Driver_getMype, Driver_abortFlash
  use RuntimeParameters_interface, ONLY : RuntimeParameters_get

  implicit none

#include "constants.h"
#include "Flash.h"

  call Driver_getMype(MESH_COMM, sim_meshMe)

  call RuntimeParameters_get('sim_pAmbient',    sim_pAmbient)
  call RuntimeParameters_get('sim_rhoAmbient',  sim_rhoAmbient)
  call RuntimeParameters_get('sim_windVel',     sim_windVel)
  call RuntimeParameters_get('sim_rhoCloud',    sim_rhoCloud)
  call RuntimeParameters_get('sim_rCloud',      sim_rCloud)
  call RuntimeParameters_get('sim_smoothWidth', sim_smoothWidth)
  call RuntimeParameters_get('sim_rvScale',     sim_rvScale)
  call RuntimeParameters_get('sim_velocityIC',  sim_velocityIC)
  if (sim_velocityIC /= 0 .and. sim_velocityIC /= 1) then
     call Driver_abortFlash('sim_velocityIC must be 0 or 1')
  endif
  if (sim_meshMe == 0) write(*,'(A,I1)') '[sensitivity] sim_velocityIC = ',sim_velocityIC
  call RuntimeParameters_get('sim_xctr',        sim_xCenter)
  call RuntimeParameters_get('sim_yctr',        sim_yCenter)
  call RuntimeParameters_get('sim_zctr',        sim_zCenter)
  call RuntimeParameters_get('gamma',           sim_gamma)
  call RuntimeParameters_get('smallp',          sim_smallP)
  call RuntimeParameters_get('smallx',          sim_smallX)
  call RuntimeParameters_get('smallt',          sim_smallT)

end subroutine Simulation_init
