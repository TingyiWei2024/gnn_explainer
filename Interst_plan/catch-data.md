Got it—discussion only, no long code. Here’s how I’d approach **automating extraction** from NBO / Multiwfn text to your two Excel templates, step by step, with division of roles.

---

## [Kirk] High-level game plan (from raw text → clean tables)

**Goal:** go from Gaussian `.log` / NBO / Multiwfn text to two tidy DataFrames:

* `nodes`: per-atom charges/populations/valence
* `edges`: per-bond bond-order metrics

**Three viable strategies (you can mix & match):**

1. **Regex + section anchors (fast to build, fully offline).**
   Identify stable **section headers** in your text (e.g., “Summary of Natural Population Analysis”, “Mayer bond order analysis”, “Wiberg bond order…”, “Mulliken overlap population”), then parse the **fixed-width tables** beneath each with `read_fwf` or regex captures. Works well if your outputs follow consistent formatting.

2. **Multiwfn batch export to CSV (most robust if available).**
   Multiwfn supports **batch / script mode**: pass a sequence of menu choices to export target tables directly as CSV/TSV. That removes most parsing brittleness and gives you machine-readable files to merge.

3. **Checkpoint-based route (if you already have `.fchk`/`.47`):**
   Some quantities (e.g., NPA charges) are accessible via formatted checkpoint and libraries (e.g., cclib) or via Multiwfn scripted extraction from `.fchk`. You still need bond orders from NBO/Multiwfn tables, so this is usually a partial solution.

**Alignment invariant:** The atom and bond indices in your Excel must match the **RDKit mol after `AddHs()`** used to generate the Gaussian input. If you wrote the Gaussian input from that RDKit geometry **without reordering atoms**, indices align 1:1 (modulo 0/1-based offset). If not, we add a one-time **coordinate matching** step to map Gaussian order → RDKit order.

---

## [Spock] Logic invariants & mapping rules (so nothing drifts)

1. **Atom index mapping (crucial):**

   * If Gaussian input was generated directly from your **H-added RDKit mol**, then
     $$ \text{atom_idx}*{\text{RDKit}} = \text{atom_idx}*{\text{Gaussian}} - 1. $$
     (Gaussian tables are typically 1-based.)
   * If not guaranteed, compute a bijection by **nearest-neighbor matching** of coordinates (RMSD-free if identical geometries). We only do this once per molecule and cache the mapping.

2. **Edge mapping:**

   * The edge list (`src<dst`) comes from RDKit bonds.
   * Bond-order tables list pairs `(i,j)` with a value. Normalize them to **sorted tuples** and join onto your RDKit edge set.
   * If an NBO table includes non-RDKit neighbor pairs (e.g., tiny long-range values), ignore them unless you intend to build **fully connected** message passing (you said you won’t).

3. **Section detection:**
   Define exact **anchor strings** you will rely on, e.g.

   * `Summary of Natural Population Analysis` → column with `q_npa`
   * `Mayer bond order analysis` → `val_mayer_tot` **(keep only total, per your decision)** and pairwise BO if present
   * `Wiberg bond order` → `bo_wiberg`
   * `Mulliken overlap population` → `bo_mull`
   * `Hirshfeld` → `q_hirsh`
   * `Mulliken population` → `pop_mull` and `q_mull`
   * `Atomic dipole corrected Hirshfeld` → `q_adch`
   * `CHELPG` → `q_chelpg`
     Each anchor implies a known **table shape** (N rows = atoms, or rows = pairs) and target output columns.

4. **Number normalization:**

   * Accept scientific notation, leading/trailing spaces, and minus signs.
   * Convert commas/locale variants to dot.
   * Clip insane outliers (e.g., charge outside `[-5,5]`) to flag likely parsing errors.

5. **Idempotence:**
   Run extractors independently per feature; then **outer-join** on `(mol_id, atom_idx)` for nodes and `(mol_id, src, dst)` for edges. This lets you add/replace features later without re-running everything.

---

## [AI-Engineer] Concrete, minimal plan to implement (no code yet)

**Inputs you already have**

* `molecules.xlsx` (mol_id ↔ SMILES mapping)
* C24 `.log` (and others later) + any Multiwfn text outputs

**Output files**

* `node_features.xlsx` (`nodes` sheet)
* `edge_features.xlsx` (`edges` sheet)

**Pipeline sketch**

1. **Load molecule list** (`mol_id`, `smiles`). Build RDKit mol with `AddHs()`; store:

   * atom count `N`
   * RDKit bond set `E = {(u,v) | u<v}`
2. **For each mol_id**, parse its text outputs with a **tiny extractor per feature group**:

   * **Per-atom tables** → DataFrame with `(atom_idx, value)`; adjust 1-based → 0-based; apply mapping if needed; add `mol_id`.
   * **Per-pair tables** → DataFrame with `(i,j,value)`; convert to 0-based; normalize `(min(i,j), max(i,j))`; **inner-join** with RDKit `E` so only bonded pairs survive; add `mol_id`.
3. **Merge** all per-atom frames (outer-join on `(mol_id, atom_idx)`), rename to:
   `q_npa, val_mayer_tot, q_hirsh, pop_mull, q_mull, q_adch, q_chelpg`.
4. **Merge** all per-edge frames (outer-join on `(mol_id, src, dst)`), rename to:
   `bo_mayer_abs, bo_wiberg, bo_mull`.

   * If your Mayer table isn’t absolute, take `abs(value)`.
5. **Augment nodes** with `element`, `is_H` from RDKit; **validate**:

   * uniqueness: `(mol_id, atom_idx)` and `(mol_id, src, dst)`
   * completeness: atom count matches RDKit; edge pairs subset of RDKit bonds
6. **Export** to the templates.

**Quality checks to include**

* Sum of atomic charges (NPA / Mulliken / ADCH / CHELPG) ≈ **total charge** (0) within tolerance.
* Per-edge BOs in plausible ranges (e.g., `0 ≤ Wiberg ≤ 2.5` typical).
* Spot-check C24 vs the raw table.

**When you don’t want to copy-paste**

* Prefer **batchable extraction**:

  * Use **fixed section anchors + `read_fwf`**: most NBO & Multiwfn tables are fixed-width; this reduces regex pain.
  * Or trigger **Multiwfn in batch** with an input script that selects the menu → exports CSV—zero manual work.
* Keep a **feature manifest** (YAML/JSON): for each feature, store:
  `anchor_string`, `table_type` (`atom`/`pair`), `col_positions` (for FWF), `target_column_name`, `postproc` (`abs`, unit scale).
  Then your extractor is data-driven and easy to adjust if formatting shifts slightly.

**Edge cases**

* If Gaussian reordered atoms (rare but possible when you re-optimized with different tools), compute a **coordinate mapping** once and cache it.
* If Multiwfn prints hydrogens at the end (some modes do), verify by counting and mapping before trusting indices.

---

If you’re happy with this plan, we can:

* lock the **feature manifest** (names + anchors + table shapes), and
* implement **small, reusable extractors** (one for per-atom sections, one for per-pair sections), plus a **validator**.

Say the word and I’ll draft the manifest and tiny function signatures (just names & docstrings) so you can see the skeleton before we write real code.
