import sys
import os
from pathlib import Path
import uvicorn

# Ensure the workspace root is in sys.path and PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Update PYTHONPATH for Uvicorn reload subprocesses on Windows
current_pythonpath = os.environ.get("PYTHONPATH", "")
if str(ROOT_DIR) not in current_pythonpath:
    os.environ["PYTHONPATH"] = f"{ROOT_DIR}{os.pathsep}{current_pythonpath}" if current_pythonpath else str(ROOT_DIR)

if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(BACKEND_DIR)],
        log_level="info",
    )
