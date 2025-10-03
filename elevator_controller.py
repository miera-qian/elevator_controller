#!/usr/bin/env python3
"""
Elevator Controller - Main Entry Point

This script runs the elevator scheduling algorithm.
You can switch between different algorithms by importing them from the algo package.
"""

from algo import OptimizedScanAlgorithm

# You can switch to a different algorithm by changing the import and instantiation:
# from algo import MyCustomAlgorithm
# algorithm = MyCustomAlgorithm()


if __name__ == "__main__":
    # Create and start the algorithm
    algorithm = OptimizedScanAlgorithm()
    algorithm.start()
