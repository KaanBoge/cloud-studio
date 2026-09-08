# Cloud-crushing 3D SPH, MIXED PRECISION variant for the level-6 memory test.
# Identical physics to Config_3d.sh; only the internal storage precision differs.
PERIODIC
NTYPES=2
LONG_Y_BITS=1
LONG_Z_BITS=1
DOUBLEPRECISION=2
POSITIONS_IN_32BIT
OUTPUT_PRESSURE
