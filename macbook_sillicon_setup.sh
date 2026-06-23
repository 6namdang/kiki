#!/bin/bash

set -e

echo "Setting up MonkBook...."

python --version | grep "3.12.10" || {
    echo "Error: Python 3.12.10 required"
    exit 1
}

python3 -m venv venv

source venv/bin/activate

pip3 install --upgrade pip3

pip install -e ".[dev]"

echo "Environment ready! Activate with: source venv/bin/activate"

