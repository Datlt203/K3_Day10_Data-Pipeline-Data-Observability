from __future__ import annotations
import sys

from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from pipelines.corruption_flow import main


if __name__ == "__main__":
    main()
