import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.app import main

if __name__ == "__main__":
    main()
