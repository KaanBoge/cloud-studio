!!****if* source/Simulation/SimulationMain/WindTunnel/Grid_applyBCEdge
!!
!! NAME
!!  Grid_applyBCEdge
!!
!! SYNOPSIS
!!
!!  Grid_applyBCEdge(integer(IN)              :: bcType, 
!!                   integer(IN)              :: bcDir,
!!                   integer(IN)              :: guard,
!!                   integer(IN)              :: var,
!!                   real(INOUT),dimension(:) :: dataRow(2*guard),
!!                   integer(IN)              :: face,
!!                   integer(IN)              :: gridDataStruct,
!!                   integer(IN),OPTIONAL     :: blockHandle,
!!                   real(in),OPTIONAL    :: secondCoord,
!!                   real(in),OPTIONAL    :: thirdCoord)
!!  
!!                    
!!  
!! DESCRIPTION 
!!  
!!  Applies the boundary conditions to a given vector.
!!  This routine applies the boundary conditions on a given face (lowerface
!!  or upperface) of a given vector. 
!!     If (face=LOW)dataRow(1:guard) = boundary values
!!     If (face=HIGH) dataRow(guard+1:2*guard) = boundary values
!!  The reason why information about direction and variable is included in
!!  this interface is because velocities need to be treated specially
!!  for REFLECTING boundary conditions. 
!!  This implementation is specific to the WindTunnel problem which 
!!  requires inflow and outflow boundary conditions.
!!
!!
!!  
!! ARGUMENTS 
!!
!!
!!  bcType -   the type of boundary condition being applied to this face
!!              -  USER_DEFINED: This routine does its own thing.
!!              -  other types:  This routine reproduces the actions of the Grid unit's
!!                 own implementation (at least for cases that may occur in the
!!                 WindTunnel simulation.)     
!!  bcDir -    can take on values IAXIS,JAXIS or KAXIS. This is needed
!!             for handling the reflective boundary conditions. If bcDir=IAXIS,
!!             and boundary conditions are reflective, and X velocity is
!!             treated differently from all other variables. similarly if bcDir
!!             is JAXIS, then Y velocity is different.
!!  guard -    number of guardcells 
!!  var   -    The variable on which boundary conditions are applied
!!             It is used with bcDir for reflective boundary conditions
!!             to correctly handle velocities. This argument is redundant 
!!             for all other variables.
!!  dataRow -  storage for the data being operated upon.
!!  face    -  can take values LOW and HIGH, defined in constants.h
!!             to indicate whether to apply boundary on lowerface or 
!!             upperface
!!  gridDataStruct : integer value specifying data structure. 
!!                   The options are defined in constants.h and they are :
!!                   CENTER cell centered variables (unk or work for PM) (default)
!!                   FACEX  face centered variable on faces along IAXIS
!!                   FACEY  face centered variable on faces along JAXIS
!!                   FACEZ  face centered variable on faces along IAXIS
!!
!!   blockHandle - the identity of the block under consideration
!!  secondCoord,thirdCoord - scalar coordinate values in the coordinate
!!                         directions perpendicular to the sweep direction.
!!                         This is not needed for simple boundary condition types
!!                         such as REFLECTIVE or OUTFLOW, but is provided so that
!!                         more complex boundary conditions can make use of it.
!!  NOTES 
!!            This routine exists in the simulation directory of 
!!            the WindTunnel problem, and therefore replaces
!!            the default implementation in the Grid unit.
!!            
!!
!!***


subroutine Grid_applyBCEdge(bcType,bcDir,guard,var,dataRow,face,&
     gridDataStruct, blockHandle, secondCoord, thirdCoord)
  use Simulation_data, ONLY: sim_pAmbient, sim_rhoAmbient, sim_windVel, sim_gamma, &
     &  sim_smallP, sim_smallX
  use Driver_interface, ONLY : Driver_abortFlash
  use Grid_data, ONLY :gr_meshMe                   ! only needed for print* in error case
  implicit none

# include "constants.h"
# include "Flash.h"

  integer, intent(in):: bcType
  integer,intent(IN) :: var,guard,face,bcDir,gridDataStruct
  real,dimension(:),intent(INOUT)::dataRow
  integer,intent(IN),OPTIONAL :: blockHandle
  real,intent(IN),OPTIONAL :: secondCoord,thirdCoord
  real :: kine
  integer :: i     !loop counter
  integer :: k, sign

  if (gridDataStruct/=CENTER) then
     print*,'boundary is',bcType,gr_meshMe,face,gridDataStruct
     call Driver_abortFlash("[Grid_applyBCEdge] Simulation WindTunnel does not support face variables")
  end if

  sign = 1
  if (gridDataStruct==CENTER) then
#ifdef VELX_VAR
     if ((bcDir==IAXIS).and.(var==VELX_VAR))sign=-1
#endif
#ifdef VELY_VAR
     if((bcDir==JAXIS).and.(var==VELY_VAR))sign=-1
#endif
#ifdef VELZ_VAR
     if((bcDir==KAXIS).and.(var==VELZ_VAR))sign=-1
#endif
  end if


  if((bcType)==PERIODIC) return

  if(face==LOW) then
     select case (bcType)
     case(REFLECTING)
        k = 2*guard+1
        do i = 1,guard
          dataRow(i)= dataRow(k-i)*sign
        end do
     case(OUTFLOW)
        do i = 1,guard
           dataRow(i)= dataRow(guard+1)
        end do
     case(USER_DEFINED)
        select case(var)
        case(GAMC_VAR)
           dataRow(1:guard)=sim_gamma
        case(GAME_VAR)
           dataRow(1:guard)=sim_gamma
        case(DENS_VAR)
           dataRow(1:guard)=sim_rhoAmbient
        case(PRES_VAR)
           dataRow(1:guard)=sim_pAmbient
        case(VELX_VAR)
           dataRow(1:guard)=sim_windVel
        case(VELY_VAR)
           dataRow(1:guard)=0.0
        case(VELZ_VAR)
           dataRow(1:guard)=0.0
        case(ENER_VAR)
           kine = 0.5 * (sim_windVel**2)
           dataRow(1:guard) = max( sim_pAmbient / ((sim_gamma-1.) * sim_rhoAmbient) + kine, sim_smallP)
        case(EINT_VAR)
           dataRow(1:guard) = max( sim_pAmbient / ((sim_gamma-1.) * sim_rhoAmbient), sim_smallP)
        case(SPECIES_BEGIN)
           dataRow(1:guard)=1.0e0-sim_smallX
        case(SPECIES_BEGIN+1)
           dataRow(1:guard)=sim_smallX
        end select


     case default
        call Driver_abortFlash("unsupported boundary condition on Lower Face")
     end select
  else
     
     select case (bcType)
     case(REFLECTING)
        k = 2*guard+1
        do i = 1,guard
           dataRow(k-i)= dataRow(i)*sign
        end do
        
     case(OUTFLOW)
        do i = 1,guard
           dataRow(guard+i)= dataRow(guard)
        end do
     case(USER_DEFINED)
        print*,'boundary is',bcType,gr_meshMe,face
        call Driver_abortFlash("Simulation WindTunnel does not support USER_DEFINED boundary on Upper Face")
     case default
        print*,'boundary is',bcType,gr_meshMe
        call Driver_abortFlash("unsupported boundary condition on Upper Face")
     end select
  end if
  return
end subroutine Grid_applyBCEdge

