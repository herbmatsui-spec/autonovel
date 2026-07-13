import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

from kernels.comfort import ComfortKernel

try:
    kernel = ComfortKernel()
    print("SUCCESS: ComfortKernel instantiated.")
except TypeError as e:
    print(f"FAILED: {e}")
except Exception as e:
    print(f"ERROR: {e}")

