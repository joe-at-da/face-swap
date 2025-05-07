#!/bin/bash
# Script to fix NumPy and OpenCV compatibility issues

# Downgrade NumPy to a version compatible with OpenCV
pip uninstall -y numpy
pip install -r /app/backend/requirements-numpy-fix.txt

# Print versions for verification
echo "NumPy version after fix:"
python -c "import numpy; print(numpy.__version__)"
echo "OpenCV version after fix:"
python -c "import cv2; print(cv2.__version__)"

echo "NumPy and OpenCV compatibility fix completed!"
