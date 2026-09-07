"""Strict native-data exporter. Legacy positional arguments are no longer accepted."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'verified_20260907'))
from dense_export_v2 import main
if __name__=='__main__':main()
