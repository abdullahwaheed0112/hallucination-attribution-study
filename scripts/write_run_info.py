"""Record library versions and random seeds in results/run_info.json (merges; later steps add their seeds).
Usage: python -I scripts/write_run_info.py <results folder> [name=value ...]   e.g. item_selection_seed=20261113
"""
import json, pathlib, platform, sys
out = pathlib.Path(sys.argv[1]) / "run_info.json"
info = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"seeds": {}}
v = {"python": platform.python_version(), "platform": platform.platform()}
for m in ("numpy", "scipy", "pandas", "statsmodels", "matplotlib", "pypdf"):
    try:
        v[m] = __import__(m).__version__
    except Exception as e:  # not installed
        v[m] = "not available"
info["versions"] = v
for kv in sys.argv[2:]:
    k, val = kv.split("=", 1)
    info["seeds"][k] = int(val)
out.write_text(json.dumps(info, indent=1), encoding="utf-8")
print(json.dumps(info, indent=1))
