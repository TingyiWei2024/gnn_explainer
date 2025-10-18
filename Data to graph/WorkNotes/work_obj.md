# BDE
## 10.13 (得解决alfabet环境问题)
目标：SMILES → RDKit → (alfabet)BDE → Graph(pkl) → 训练 全流程复现一次。
验收产物：
graph_bde.pkl 或 *.pt 成功生成（含 x/edge_index/edge_attr/y）

训练脚本能跑出 epoch 10 | loss... | acc...（截图+日志）

code summary:
1. env import
安装 alfabet==0.2.2，导入 RDKit / NetworkX / pandas
-> Q1 of model input in work_QA.md

2. BDE 预测入口
  → canonicalize_smiles → check_input
  → predict_bdes(can_smiles)  # per-bond predictions
      → drop_duplicates(['fragment1','fragment2'])
-> Q2 

3. 建graph把bde/bdfe打包进edge_features      
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

4. 核心：
- 节点顺序：重原子优先且顺序与 RDKit（未加氢）一致；再接在后面的才是 H 节点。
- 边集合：无向图统一成 (min(u,v), max(u,v)) 的唯一表述；如需传给 GNN 的“无向”，在 edge_index 里再复制一份反向边。
- 列顺序：edge_attr 的列（比如 [bde_pred, bdfe_pred, bond_index]）要固定顺序，并写入一个 features_spec.json，供训练与解释器使用。

# NBO
## 10.15
今日Mission：
1️⃣ 解析 Excel 节点与边表；
2️⃣ 构建 NetworkX 图并成功保存为 graph_nbo.pkl；
3️⃣ 转化为 PyG Data 对象并验证 Data(x, edge_index, edge_attr)；
4️⃣ 若时间许可，执行 GCN 测试循环并推送至数据库。

1. NBO FEATURES 整理
-> 见nbo_features.md
2. excel c24 sample 建立

## 10.16 - continue 10.15 obj
1.index alignment between NBO outputs and the RDKit graph
- mol = MolFromSmiles(smiles) → can_smiles = MolToSmiles(mol, canonical=True)
- mol_can = MolFromSmiles(can_smiles) → mol_H = AddHs(mol_can)

10.17 
1. create assumed node and edge datasets

10.18
1️⃣ Data Intake
2️⃣ Graph Construction
3️⃣ Model Input Validation
4️⃣ Training Pipeline
5️⃣ Save/Load Functionality
