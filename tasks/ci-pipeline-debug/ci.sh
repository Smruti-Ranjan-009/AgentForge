#!/bin/bash
set -euo pipefail
cd /tmp
pytest -q tests/test_app.py
