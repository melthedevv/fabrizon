"""Double-click to open Fabrizon. (Made by melthedev - https://ko-fi.com/melthedev)"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from fabrizon.gui import serve

raise SystemExit(serve())
