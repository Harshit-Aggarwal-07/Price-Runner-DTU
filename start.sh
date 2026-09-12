#!/bin/bash
echo "=========================================="
echo "  DTU Grocery Price Compare - Setup"
echo "=========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Please install Python 3.10+."
    exit 1
fi

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv venv
fi

# Activate
echo "[2/3] Activating virtual environment..."
source venv/bin/activate

# Install
echo "[3/3] Installing dependencies..."
pip install -r requirements.txt -q

echo ""
echo "=========================================="
echo "  Starting Server..."
echo "  Open http://localhost:8000"
echo "=========================================="
echo ""

python main.py
