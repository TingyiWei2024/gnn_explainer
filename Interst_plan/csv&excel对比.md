**CSV vs. Excel for model input**

* **CSV — generally suitable (and preferred)**

  * ✅ Simple, fast I/O in Python; no heavy dependencies.
  * ✅ Git-friendly diffs; stable in pipelines/CI.
  * ✅ No hidden formatting, merged cells, or formulas.
  * ⚠️ Text-only types; you must enforce dtypes yourself (which is good for reproducibility).
* **Excel (XLSX) — avoid for model ingestion**

  * ❌ Slow/fragile; needs engines (`openpyxl`, etc.).
  * ❌ Easy to introduce invisible errors (auto-dates, merged cells, locale quirks).
  * ❌ Painful in headless/cluster environments and code reviews.

**Best practice combo**

* **Authoring/inspection:** XLSX is fine for *humans* upstream.
* **Ingestion:** export to **CSV** (or better, **Parquet** for large data: typed, compressed, columnar).
* **Artifacts:** keep `nodes_standardized.csv`, `edges_standardized.csv`; optionally mirror as `nodes.parquet`, `edges.parquet`; archive final tensors as `.pt/.npz`.

