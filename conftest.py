import pathlib
import sys

# bin/ is a folder of scripts, not a package; put it on the path so tests can import them.
BIN = pathlib.Path(__file__).resolve().parent / "bin"
sys.path.insert(0, str(BIN))
