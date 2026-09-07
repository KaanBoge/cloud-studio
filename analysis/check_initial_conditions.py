"""See verified_20260907/check_snapshot.py for explicit native-grid IC checks."""
import runpy
from pathlib import Path
import sys
root=Path(__file__).resolve().parent/'verified_20260907'
sys.path.insert(0,str(root))
if __name__=='__main__': runpy.run_path(str(root/'check_snapshot.py'),run_name='__main__')
