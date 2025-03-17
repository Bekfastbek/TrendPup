#!/bin/bash

if ! dpkg -l | grep -q xvfb; then
    echo "Installing Xvfb..."
    sudo apt-get update
    sudo apt-get install -y xvfb x11-utils xvfb
fi

sudo apt-get install -y \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libnss3 \
    libcups2 \
    libxss1 \
    libxrandr2 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    libgbm1 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils

pkill Xvfb || true

Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

sleep 2

echo "Starting scraper..."
python3 scraper.py

echo "Starting Gemini analyzer..."
python3 gemini_analyzer.py

pkill Xvfb