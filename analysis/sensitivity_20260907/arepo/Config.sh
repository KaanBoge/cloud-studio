#!/bin/bash
## Config.sh for 3D cloud-crushing (cloud-wind matched setup)
## periodic long box 20x10x10 via BoxSize=10 + LONG_X=2
## transverse faces y and z are OUTFLOW (REFLECTIVE_*=2), x stays periodic
## so the wind supply is never cut off.

#--------------------------------------- Basic operation mode of code
LONG_X=2.0                               # stretch x extent: 2 x BoxSize(10) = 20

#--------------------------------------- Hydrodynamics (defaults: GAMMA=5/3 ideal hydro)
PASSIVE_SCALARS=1                        # cloud-material tracer

#--------------------------------------- Mesh motion and regularization
REGULARIZE_MESH_CM_DRIFT                 # move mesh-generating point towards center of mass
REGULARIZE_MESH_CM_DRIFT_USE_SOUNDSPEED  # limit regularization speed by local sound speed
REGULARIZE_MESH_FACE_ANGLE               # roundness criterion: max face angle

#--------------------------------------- Time integration options
TREE_BASED_TIMESTEPS                     # non-local timestep criterion (signal speed)

#---------------------------------------- Single/Double Precision
DOUBLEPRECISION=1
INPUT_IN_DOUBLEPRECISION
OUTPUT_IN_DOUBLEPRECISION
OUTPUT_CENTER_OF_MASS

#--------------------------------------- Output/Input options
HAVE_HDF5
REFLECTIVE_Y=2   # 2 = inflow/outflow: the transverse y faces are no longer periodic
REFLECTIVE_Z=2   # 2 = inflow/outflow: the transverse z faces are no longer periodic
