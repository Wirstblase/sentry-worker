#!/usr/bin/env bash
# run.sh - Unix run script

if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run ./setup.sh first."
    exit 1
fi

source venv/bin/activate

echo "Starting Sentry Stream Processor..."
python main.py
