#!/bin/bash
set -e

echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

echo "Installing dependencies with pre-built wheels only..."
pip install --only-binary=:all: --no-cache-dir -r requirements.txt

echo "Verifying installation..."
python -c "import fastapi, pydantic, uvicorn; print('All imports successful')"