SMILES → RDKit(mol) → alfabet(BDE/ BDFE) → build_graph():
   - nodes: x=[N, F_bde]
   - edges: edge_index=[2, E], edge_attr=[E, F_edge_bde]
 → pack(Data) → dump_pickle(.pkl/.pt)
 → MetaNet_train.py(load) → split → train/val/test → metrics → save(model.pt, logs)
 → optuna_train.py(study) → gnn_explainer.py

关键文件/函数：
- scripts/xyz.py: build_graph_from_smiles(...)
- scripts/abc.py: standardize(X, fit_on_train)
- configs/*.yaml: 超参、路径


SMILES -> Graph - BDE/BDFE
SMILES list
  → canonicalize_smiles → check_input
  → predict_bdes(can_smiles)  # per-bond predictions
      → drop_duplicates(['fragment1','fragment2'])
  → create_bde_graph_selective_hs(smiles, bde_df)
      - Build RDKit heavy-atom Mol (no Hs)
      - Nodes: heavy atoms (int ids)
      - Edges: skeleton heavy-heavy bonds from Mol
      - For each predicted row:
          * if heavy-heavy: update or add edge with bde/bdfe
          * if heavy-H: add 'H_x' node + heavy–H edge with bde/bdfe
  → (optional) bde_df['nx_graph'] = graph
→ concat all dfs → alfabet_results_022
→ save graphs: gpickle_graph_{i}.pkl
