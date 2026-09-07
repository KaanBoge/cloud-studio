"""Native-data figure comparison; the legacy mesh-only claims are retired."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'verified_20260907'))
from figure1_v2 import main
if __name__=='__main__': main()
