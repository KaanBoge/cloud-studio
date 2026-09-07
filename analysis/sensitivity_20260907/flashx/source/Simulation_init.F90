!!****if* source/Simulation/SimulationMain/CloudWind/Simulation_init
!!
!! NAME
!!  Simulation_init
!!
!! SYNOPSIS
!!  call Simulation_init()
!!
!! DESCRIPTION
!!  Initializes the runtime parameters for the CloudWind (cloud crushing)
!!  problem.  Flash-X port of the FLASH 4.8 CloudCrush Simulation_init.
!!
!!***

subroutine Simulation_init()

  use Simulation_data
  use RuntimeParameters_interface, ONLY : RuntimeParameters_get
  use Driver_interface, ONLY : Driver_getMype, Driver_abort

  implicit none

#include "constants.h"
#include "Simulation.h"

  call Driver_getMype(MESH_COMM, sim_meshMe)

  call RuntimeParameters_get('sim_pAmbient',   sim_pAmbient)
  call RuntimeParameters_get('sim_rhoAmbient', sim_rhoAmbient)
  call RuntimeParameters_get('sim_windVel',    sim_windVel)
  call RuntimeParameters_get('sim_rhoCloud',   sim_rhoCloud)
  call RuntimeParameters_get('sim_rCloud',     sim_rCloud)
  call RuntimeParameters_get('sim_smoothWidth',sim_smoothWidth)
  call RuntimeParameters_get('sim_rvScale',    sim_rvScale)
  call RuntimeParameters_get('sim_velocityIC', sim_velocityIC)
  if (sim_velocityIC /= 0 .and. sim_velocityIC /= 1) &
       call Driver_abort('sim_velocityIC must be 0 or 1')
  if (sim_meshMe == 0) write(*,'(A,I0)') '[sensitivity] sim_velocityIC = ', sim_velocityIC
  call RuntimeParameters_get('sim_xctr',       sim_xCenter)
  call RuntimeParameters_get('sim_yctr',       sim_yCenter)
  call RuntimeParameters_get('sim_zctr',       sim_zCenter)
  call RuntimeParameters_get('gamma',          sim_gamma)
  call RuntimeParameters_get('smallp',         sim_smallP)
  call RuntimeParameters_get('smallx',         sim_smallX)
  call RuntimeParameters_get('smallt',         sim_smallT)

end subroutine Simulation_init
