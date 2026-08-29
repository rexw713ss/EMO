"""
情緒辨識主入口 (main.py)
重新導向至優化後的四階段展示系統 (demo.py)
"""

import sys
import os

# 確保當前目錄在 path 中
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from demo import main

if __name__ == "__main__":
    main()