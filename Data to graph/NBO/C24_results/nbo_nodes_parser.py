# nbo_nodes_parser.py
# ------------------------------------------------------------
# Parse per-atom node features from NBO/Multiwfn text exports
# and merge into your node Excel (sheet="nodes").
# ------------------------------------------------------------

import re
import pandas as pd
from pathlib import Path
from typing import Dict, Optional

# ---------- Core merge helper ----------

def merge_into_node_excel(
    node_xlsx: str,
    df_feature: pd.DataFrame,
    feature_cols: Optional[list] = None,
    readme_source_xlsx: Optional[str] = None
):
    """
    Merge df_feature (must contain mol_id, atom_idx) into node_xlsx.
    - If node_xlsx doesn't exist, it will be created (empty 'nodes' sheet).
    - If readme_source_xlsx provided and node_xlsx is being created,
      copy its README sheet to the new file.
    - Only fills missing values; preserves existing non-null cells.
    """
    node_path = Path(node_xlsx)
    creating = not node_path.exists()

    if creating:
        # Create an empty nodes table with expected schema
        base_cols = [
            "mol_id", "atom_idx", "element", "is_H",
            "q_npa", "val_mayer_tot", "q_hirsh", "pop_mull",
            "q_mull", "q_adch", "q_chelpg"
        ]
        nodes = pd.DataFrame(columns=base_cols)
        readme_df = None
        if readme_source_xlsx:
            try:
                readme_df = pd.read_excel(readme_source_xlsx, sheet_name="README")
            except Exception:
                readme_df = None
    else:
        sheets = pd.read_excel(node_path, sheet_name=None)
        nodes = sheets.get("nodes", pd.DataFrame())
        readme_df = sheets.get("README", None)

        # If file exists but 'nodes' missing, create it
        if nodes.empty:
            base_cols = [
                "mol_id", "atom_idx", "element", "is_H",
                "q_npa", "val_mayer_tot", "q_hirsh", "pop_mull",
                "q_mull", "q_adch", "q_chelpg"
            ]
            nodes = pd.DataFrame(columns=base_cols)

    # Ensure key columns present
    for c in ["mol_id", "atom_idx"]:
        if c not in nodes.columns:
            nodes[c] = pd.NA

    # Merge
    nodes = nodes.merge(
        df_feature,
        on=["mol_id", "atom_idx"],
        how="outer",
        suffixes=("", "_new"),
    )

    # Determine which feature columns to fill
    if feature_cols is None:
        feature_cols = [c for c in df_feature.columns if c not in ("mol_id", "atom_idx")]

    # Prefer existing non-null; otherwise take _new
    for col in feature_cols:
        if col not in nodes.columns:
            nodes[col] = pd.NA
        if col + "_new" in nodes.columns:
            nodes[col] = nodes[col].where(nodes[col].notna(), nodes[col + "_new"])
            nodes.drop(columns=[col + "_new"], inplace=True, errors="ignore")

    # Clean up any leftover *_new columns (from element/is_H)
    for col in list(nodes.columns):
        if col.endswith("_new"):
            base = col[:-4]
            if base in nodes.columns:
                nodes[base] = nodes[base].where(nodes[base].notna(), nodes[col])
            nodes.drop(columns=[col], inplace=True, errors="ignore")

    # Save
    with pd.ExcelWriter(node_path, engine="xlsxwriter") as w:
        nodes.to_excel(w, sheet_name="nodes", index=False)
        if readme_df is not None:
            readme_df.to_excel(w, sheet_name="README", index=False)

# ---------- Generic per-atom parsers ----------

def _df_basic_atom_table(rows, value_map: Dict[str, str]):
    """
    Build a DataFrame with mandatory keys + any value columns from value_map.
    rows is a list of dicts with keys: mol_id, atom_idx, element, maybe is_H, and values.
    """
    df = pd.DataFrame(rows).sort_values("atom_idx").reset_index(drop=True)
    if "element" in df.columns and "is_H" not in df.columns:
        df["is_H"] = (df["element"].str.upper() == "H").astype(int)
    # Keep only announced columns
    keep = ["mol_id", "atom_idx", "element", "is_H"] + list(value_map.values())
    keep = [c for c in keep if c in df.columns]
    return df[keep]

# 1) NPA (C24-ChargeFlog)  → q_npa
def parse_npa_charges(path: str, mol_id: str) -> pd.DataFrame:
    """
    Parse 'Summary of Natural Population Analysis' lines:
      Element  Index  NaturalCharge  Core  Valence  Rydberg  Total
    We only need the 'NaturalCharge' (first numeric after element+index).
    """
    pat = re.compile(
        r"^\s*([A-Za-z])\s+(\d+)\s+([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)\s+",
        flags=re.M
    )
    rows = []
    raw = Path(path).read_text(encoding="utf-8", errors="ignore")
    for m in pat.finditer(raw):
        elem = m.group(1)
        idx1 = int(m.group(2))
        q = float(m.group(3))
        rows.append({
            "mol_id": mol_id,
            "atom_idx": idx1 - 1,
            "element": elem,
            "is_H": 1 if elem.upper() == "H" else 0,
            "q_npa": q
        })
    if not rows:
        raise ValueError(f"NPA parse failed: {path}")
    return _df_basic_atom_table(rows, {"q_npa":"q_npa"})

# 2) Mayer total valence (9-1-n) → val_mayer_tot (ignore free valence)
def parse_mayer_total_valence(path: str, mol_id: str) -> pd.DataFrame:
    """
    Lines like: 'Atom   i(X ):  <total>  <free>'
    """
    pat = re.compile(
        r"Atom\s+(\d+)\((\w)\s*\)\s*:\s*([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)\s+([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)"
    )
    rows = []
    raw = Path(path).read_text(encoding="utf-8", errors="ignore")
    for m in pat.finditer(raw):
        idx1 = int(m.group(1))
        elem = m.group(2)
        val_total = float(m.group(3))
        rows.append({
            "mol_id": mol_id,
            "atom_idx": idx1 - 1,
            "element": elem,
            "is_H": 1 if elem.upper() == "H" else 0,
            "val_mayer_tot": val_total
        })
    if not rows:
        raise ValueError(f"Mayer total valence parse failed: {path}")
    return _df_basic_atom_table(rows, {"val_mayer_tot":"val_mayer_tot"})

# 3) Mulliken population + net charge (7-5-4) → pop_mull, q_mull
def parse_mulliken_pop_and_charge(path: str, mol_id: str) -> pd.DataFrame:
    """
    Lines like:
    'Atom   i(X )    Population:  6.42324137    Net charge: -0.42324137'
    """
    pat = re.compile(
        r"Atom\s+(\d+)\((\w)\s*\)\s+Population:\s*([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)\s+Net\s+charge:\s*([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)"
    )
    rows = []
    raw = Path(path).read_text(encoding="utf-8", errors="ignore")
    for m in pat.finditer(raw):
        idx1 = int(m.group(1))
        elem = m.group(2)
        pop = float(m.group(3))
        qnet = float(m.group(4))
        rows.append({
            "mol_id": mol_id,
            "atom_idx": idx1 - 1,
            "element": elem,
            "is_H": 1 if elem.upper() == "H" else 0,
            "pop_mull": pop,
            "q_mull": qnet
        })
    if not rows:
        raise ValueError(f"Mulliken 7-5-4 parse failed: {path}")
    return _df_basic_atom_table(rows, {"pop_mull":"pop_mull", "q_mull":"q_mull"})

# 4) ADCH (7-11-1) → q_adch
def parse_adch(path: str, mol_id: str) -> pd.DataFrame:
    """
    Lines like: 'Atom  i(X ):  value'
    """
    pat = re.compile(r"Atom\s+(\d+)\((\w)\s*\):\s*([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)")
    rows = []
    raw = Path(path).read_text(encoding="utf-8", errors="ignore")
    for m in pat.finditer(raw):
        idx1 = int(m.group(1))
        elem = m.group(2)
        val = float(m.group(3))
        rows.append({
            "mol_id": mol_id,
            "atom_idx": idx1 - 1,
            "element": elem,
            "is_H": 1 if elem.upper() == "H" else 0,
            "q_adch": val
        })
    if not rows:
        raise ValueError(f"ADCH 7-11-1 parse failed: {path}")
    return _df_basic_atom_table(rows, {"q_adch":"q_adch"})

# 5) CHELPG (7-12-1) → q_chelpg
def parse_chelpg(path: str, mol_id: str) -> pd.DataFrame:
    """
    Table like:
      '   1(C )   0.0118295'
    """
    pat = re.compile(r"^\s*(\d+)\((\w)\s*\)\s+([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)", flags=re.M)
    rows = []
    raw = Path(path).read_text(encoding="utf-8", errors="ignore")
    for m in pat.finditer(raw):
        idx1 = int(m.group(1))
        elem = m.group(2)
        val = float(m.group(3))
        rows.append({
            "mol_id": mol_id,
            "atom_idx": idx1 - 1,
            "element": elem,
            "is_H": 1 if elem.upper() == "H" else 0,
            "q_chelpg": val
        })
    if not rows:
        raise ValueError(f"CHELPG 7-12-1 parse failed: {path}")
    return _df_basic_atom_table(rows, {"q_chelpg":"q_chelpg"})

# 6) Hirshfeld atomic charge (7-1-1) → q_hirsh
def parse_hirshfeld_7_1_1(path: str, mol_id: str) -> pd.DataFrame:
    """
    Lines typically look like:
      'Atom    1(C ):    -0.0487'
    We capture the atom index, element, and the Hirshfeld charge value.
    """
    import re, pandas as pd
    from pathlib import Path

    pat = re.compile(r"Atom\s+(\d+)\((\w)\s*\):\s*([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)")
    raw = Path(path).read_text(encoding="utf-8", errors="ignore")

    rows = []
    for m in pat.finditer(raw):
        idx1 = int(m.group(1))
        elem = m.group(2)
        val  = float(m.group(3))
        rows.append({
            "mol_id": mol_id,
            "atom_idx": idx1 - 1,                       # 0-based
            "element": elem,
            "is_H": 1 if elem.upper() == "H" else 0,
            "q_hirsh": val
        })

    if not rows:
        raise ValueError(f"Hirshfeld 7-1-1 parse failed: {path}")

    df = pd.DataFrame(rows).sort_values("atom_idx").reset_index(drop=True)
    return df[["mol_id","atom_idx","element","is_H","q_hirsh"]]


