#!/bin/bash
# Install Playwright system dependencies
# This script attempts to install dependencies using apt-get if available

if command -v apt-get &> /dev/null; then
  echo "Installing Playwright system dependencies via apt-get..."
  apt-get update -qq
  apt-get install -y -qq \
    libglib2.0-0t64 \
    libnspr4 \
    libnss3 \
    libdbus-1-3 \
    libatk1.0-0t64 \
    libatk-bridge2.0-0t64 \
    libatspi2.0-0t64 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libasound2t64 \
    libcups2t64 \
    libcairo2 \
    libpango-1.0-0 || true
  echo "Playwright dependencies installed via apt-get"
else
  echo "apt-get not available, skipping system dependency installation"
  echo "If you encounter Playwright errors, ensure system dependencies are installed"
fi
