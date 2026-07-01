"""Unit tests for verify_coverage.py script."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import pytest


def test_coverage_script_passes(tmp_path, monkeypatch):
    # Mock coverage.json file
    json_path = tmp_path / "coverage.json"
    dummy_data = {
        "totals": {
            "percent_covered": 75.5
        }
    }
    with open(json_path, "w") as f:
        json.dump(dummy_data, f)
        
    monkeypatch.chdir(tmp_path)
    # Monkeypatch subprocess to mock the raw coverage call
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    
    # Ensure root path is in sys.path
    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root_path not in sys.path:
        sys.path.insert(0, root_path)
    
    from scripts.verify_coverage import main
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 0
