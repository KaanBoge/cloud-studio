!!****if* source/Simulation/SimulationMain/CloudWind/Simulation_data
!!
!! NAME
!!  Simulation_data
!!
!! SYNOPSIS
!!  use Simulation_data
!!
!! DESCRIPTION
!!  Stores the runtime parameters of the CloudWind (cloud crushing)
!!  problem: a supersonic wind striking a dense cloud initially at rest.
!!  Flash-X port of the FLASH 4.8 CloudCrush Simulation_data.
!!
!!***

module Simulation_data

  implicit none

  !! Runtime parameters
  real, save :: sim_pAmbient, sim_rhoAmbient, sim_windVel
  real, save :: sim_rhoCloud, sim_rCloud, sim_smoothWidth, sim_rvScale
  real, save :: sim_xCenter, sim_yCenter, sim_zCenter
  real, save :: sim_gamma, sim_smallP, sim_smallX, sim_smallT

  integer, save :: sim_meshMe, sim_velocityIC

end module Simulation_data
