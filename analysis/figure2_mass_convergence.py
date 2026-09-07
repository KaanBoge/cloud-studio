"""Schema-2 convergence plotting; old mass_frac datasets are rejected."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'verified_20260907'))
from figure2_v2 import main
if __name__=='__main__': main()
