"""
Regenerate twice with the same seed and compare row counts + SHA-256 checksums.
Demonstrates deterministic generation (Step 10 of the challenge brief).
"""

from __future__ import annotations
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from .config import DATA_DIR, CSV_DIR, DEFAULT_SEED
from .generate import run


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def check(mode: str = "starter", seed: int = DEFAULT_SEED) -> bool:
    print("=== Reproducibility Check ===")
    print(f"Mode={mode}  Seed={seed}\n")

    # Run 1
    print("--- Generation pass 1 ---")
    m1 = run(mode=mode, seed=seed)
    checksums_1 = m1["checksums_sha256"]
    counts_1 = m1["row_counts"]

    # Snapshot CSVs
    snap1 = {}
    for name, digest in checksums_1.items():
        snap1[name] = digest

    # Run 2 (overwrites data/)
    print("\n--- Generation pass 2 ---")
    m2 = run(mode=mode, seed=seed)
    checksums_2 = m2["checksums_sha256"]
    counts_2 = m2["row_counts"]

    # Compare
    ok = True
    print("\n--- Comparison ---")
    all_names = sorted(set(counts_1) | set(counts_2))
    for name in all_names:
        c1 = counts_1.get(name)
        c2 = counts_2.get(name)
        d1 = checksums_1.get(name)
        d2 = checksums_2.get(name)
        count_ok = c1 == c2
        hash_ok = d1 == d2
        status = "PASS" if (count_ok and hash_ok) else "FAIL"
        if not (count_ok and hash_ok):
            ok = False
        print(f"  [{status}] {name:25s}  rows {c1} vs {c2}  sha {d1[:12]}… vs {d2[:12]}…")

    result = {
        "mode": mode,
        "seed": seed,
        "reproducible": ok,
        "pass1_counts": counts_1,
        "pass2_counts": counts_2,
    }
    out = DATA_DIR / "reproducibility_report.json"
    with open(out, "w") as f:
        json.dump(result, f, indent=2)

    if ok:
        print("\n✅ Dataset is fully reproducible under fixed seed.")
    else:
        print("\n❌ Reproducibility check FAILED.")
    print(f"Report → {out}")
    return ok


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["starter", "full"], default="starter")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = p.parse_args()
    check(mode=args.mode, seed=args.seed)


if __name__ == "__main__":
    main()
