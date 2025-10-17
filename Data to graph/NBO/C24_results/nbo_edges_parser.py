# nbo_edges_parser.py
# ------------------------------------------------------------
# Parse bond-pair (edge) features from NBO/Multiwfn text exports
# and merge them into an edge Excel (sheet="edges").
# ------------------------------------------------------------

import re
import pandas as pd
from pathlib import Path
from typing import Optional


# ---------- Core merge helper ----------

def merge_into_edge_excel(
    edge_xlsx: str,
    df_feature: pd.DataFrame,
    feature_cols: Optional[list] = None,
    readme_source_xlsx: Optional[str] = None
):
    """
    Merge df_feature (must contain mol_id, src, dst) into edge_xlsx.
    - Creates file if missing.
    - Fills only missing values; preserves existing non-null cells.
    """
    edge_path = Path(edge_xlsx)
    creating = not edge_path.exists()

    # Initialize file if needed
    if creating:
        base_cols = ["mol_id", "src", "dst", "bo_mayer_abs", "bo_wiberg", "bo_mull"]
        edges = pd.DataFrame(columns=base_cols)
        readme_df = None
        if readme_source_xlsx:
            try:
                readme_df = pd.read_excel(readme_source_xlsx, sheet_name="README")
            except Exception:
                readme_df = None
    else:
        sheets = pd.read_excel(edge_path, sheet_name=None)
        edges = sheets.get("edges", pd.DataFrame())
        readme_df = sheets.get("README", None)
        if edges.empty:
            base_cols = ["mol_id", "src", "dst", "bo_mayer_abs", "bo_wiberg", "bo_mull"]
            edges = pd.DataFrame(columns=base_cols)

    # Ensure required columns
    for c in ["mol_id", "src", "dst"]:
        if c not in edges.columns:
            edges[c] = pd.NA

    # Merge
    edges = edges.merge(
        df_feature, on=["mol_id", "src", "dst"], how="outer", suffixes=("", "_new")
    )

    # Default feature columns
    if feature_cols is None:
        feature_cols = [
            c for c in df_feature.columns if c not in ("mol_id", "src", "dst")
        ]

    # Prefer existing non-null
    for col in feature_cols:
        if col not in edges.columns:
            edges[col] = pd.NA
        if col + "_new" in edges.columns:
            edges[col] = edges[col].where(edges[col].notna(), edges[col + "_new"])
            edges.drop(columns=[col + "_new"], inplace=True, errors="ignore")

    # Save
    with pd.ExcelWriter(edge_path, engine="xlsxwriter") as w:
        edges.to_excel(w, sheet_name="edges", index=False)
        if readme_df is not None:
            readme_df.to_excel(w, sheet_name="README", index=False)


# ---------- Generic parser template ----------

def parse_bond_order_generic(path: str, mol_id: str, value_col: str, absolute=False) -> pd.DataFrame:
    """
    Generic bond-order parser for lines like:
      '#   12:   1(C )   2(C )   0.76807708'
      or '   1(C )   2(C )   0.76807708'
    - absolute=True → takes abs(value)
    - returns (mol_id, src, dst, value_col)
    """
    text = Path(path).read_text(encoding="utf-8", errors="ignore")

    pat = re.compile(
        r"^\s*#?\s*\d*:\s*(\d+)\([^)]*\)\s+(\d+)\([^)]*\)\s+([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)",
        flags=re.M,
    )

    rows = []
    for m in pat.finditer(text):
        i, j, val = int(m.group(1)), int(m.group(2)), float(m.group(3))
        src, dst = min(i, j) - 1, max(i, j) - 1  # 0-based
        val = abs(val) if absolute else val
        rows.append({"mol_id": mol_id, "src": src, "dst": dst, value_col: val})

    if not rows:
        raise ValueError(f"No bond pairs parsed in {path}")

    df = pd.DataFrame(rows).drop_duplicates(["mol_id", "src", "dst"])
    return df.sort_values(["src", "dst"]).reset_index(drop=True)


# ---------- Specific parsers ----------

def parse_mayer_bond_order(path: str, mol_id: str) -> pd.DataFrame:
    """9-1-e → bo_mayer_abs (absolute value)"""
    return parse_bond_order_generic(path, mol_id, value_col="bo_mayer_abs", absolute=True)


def parse_wiberg_bond_order(path: str, mol_id: str) -> pd.DataFrame:
    """9-3 → bo_wiberg (keep sign)"""
    return parse_bond_order_generic(path, mol_id, value_col="bo_wiberg", absolute=False)


def parse_mulliken_bond_order(path: str, mol_id: str) -> pd.DataFrame:
    """9-4 → bo_mull (keep sign)"""
    return parse_bond_order_generic(path, mol_id, value_col="bo_mull", absolute=False)



