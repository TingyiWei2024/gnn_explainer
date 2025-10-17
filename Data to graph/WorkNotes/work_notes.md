一. module input

## **Q2.关于alfabet:https://github.com/NREL/alfabet**

### 1. canonicalize_smiles

SMILES 就是“把分子写成一行字符串”的记法。但同一个分子可能有多种写法（等价）。
canonical SMILES 就是把这类等价写法统一成唯一的标准写法——像给分子“发统一身份证”
alfabet里也有：
from alfabet.fragment import canonicalize_smiles
s_can = canonicalize_smiles(s_raw)
**-> 应该是源于rdkit最开始的基础库？有时间看看**
**-> 有时间了去alfabet_canonical.md里继续研究**

### 2.索引加不加H的问题
我们的代码逻辑：计算bde前不加H / 建图得有计算出来的H的位置放bde数据，这时候加上

A. 不加H 原因：alfabet 训练的 GNN 模型是在“不加氢的分子”上训练的
-> 预测阶段禁止 AddHs()确保索引与 alfabet 完全一致

B. 加H的时机：建图时
**在建图阶段，当 alfabet 告诉我们“这里有一条 X–H 键”时，再动态补上一个 H 节点，并把它的 BDE 写进边属性**
alfabet 预测的键解离能（BDE）中，很多断裂都是 X–H 键：
C–H、O–H、N–H ……
但 RDKit 的“未加氢分子”中，没有这些显式氢。
这时如果我们只保留重原子骨架，就没地方挂 X–H 这一类 BDE 信息。

所以，我们在构图时采取一个“按需补氢”策略：
在确定c-h的条件下
- 1.先判定Hnode是否存在，没有得先加节点
- 2.把没有的加上
- 3.如果边有了，更新数值

### 💡 为什么边要写属性？
因为我们的图不仅要存结构，还要存数值。
每条边代表一个化学键，其属性包括：
bond_index: 边在 alfabet 输出里的顺序或标识；
bde_pred: 预测的键解离能；
bdfe_pred: 预测的键解离自由能。

---
如果当前预测的键是重原子–氢键：
    创建一个唯一的氢节点ID（例如 H_-1）
    如果图里没有这个氢节点：
        添加节点，属性 symbol='H'
    如果图里没有这条重–氢的边：
        添加边，并把 BDE/BDfE 写进去
    否则（已有这条边）：
        仅更新数值
---
            # Step 1: ensure the hydrogen node is present in G
            # We'll generate a unique node key for the H, e.g. "H_{hydrogen_idx}"
            # or something that won't collide with integer-based heavy nodes.
            # You could also store the actual integer if your system allows it.           
            h_node = f"H_{hydrogen_idx}"
            if not G.has_node(h_node):
                # Add the hydrogen node with minimal attributes
                G.add_node(h_node,
                           symbol='H',
                           rdkit_idx=None)  # or some other placeholder
            # Step 2: add the H–X bond or update if it already exists
            # The heavy_idx is the integer from RDKit.
            if not G.has_edge(heavy_idx, h_node):
                G.add_edge(heavy_idx, h_node,
                           bond_index=bond_index_value,
                           bde_pred=bde_pred_value,
                           bdfe_pred=bdfe_pred_value)
---

### GPT 整理生成表格
Final schemas (frozen)

node_features.xlsx → sheet nodes

mol_id — short ID (links to molecules.xlsx)

atom_idx — RDKit 0-based index after Chem.AddHs()

element — C, H, …

is_H — 0/1

q_npa — Natural charge (NPA)

val_mayer_tot — Mayer total valence

q_hirsh — Hirshfeld charge

pop_mull — Mulliken population

q_mull — Mulliken net atomic charge

q_adch — ADCH charge

q_chelpg — CHELPG charge

edge_features.xlsx → sheet edges

mol_id

src, dst — RDKit 0-based atom indices after AddHs(). Store once with src < dst.

bo_mayer_abs — |Mayer BO|

bo_wiberg — Wiberg BO (Löwdin)

bo_mull — Mulliken BO (overlap pop)

Naming choice: we’ll use src/dst (clearer for later directed expansion).

Invariants (we will validate in code):

(mol_id, atom_idx) unique in nodes.

(mol_id, src, dst) unique in edges, with src < dst.

All indices exist in the RDKit mol after AddHs.