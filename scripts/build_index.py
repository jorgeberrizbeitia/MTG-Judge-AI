# import build_index and run it once to create the initial index
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.index_utils import build_index

build_index()