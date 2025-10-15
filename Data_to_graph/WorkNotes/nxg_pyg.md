from work_obj.md
# 怎么把nx的无向图转为pyg的有向图
- 边集合：无向图统一成 (min(u,v), max(u,v)) 的唯一表述；如需传给 GNN 的“无向”，在 edge_index 里再复制一份反向边。

边集合标准化 `(min(u,v), max(u,v))` 与 GNN 无向图规则

### 🧩 背景：

NetworkX 默认的图是“无向”的，
这意味着一条边 (u,v) 和 (v,u) 是**同一条边**。

但是 PyTorch Geometric（PyG）等 GNN 框架用的是**有向 edge_index** 表示法：

```python
edge_index = tensor([[u1, u2, u3, ...],
                     [v1, v2, v3, ...]])
```

这里的每一列 `(ui, vi)` 被视为一条**有向边**。

---

### ⚙️ 所以问题是：

> NetworkX 里边是无向的，
> 但 GNN 模型需要显式写出所有方向。

---

### ✅ 解决方法：

#### （1）**边集合统一格式**

在导出边表或准备传给 PyG 前，
我们统一每条无向边的存储格式为：

```python
(min(u, v), max(u, v))
```

例如：

```
(1, 3)
(2, 5)
(0, 4)
```

这样：

* 无论你在遍历 NetworkX 的边时遇到 `(3,1)` 还是 `(1,3)`，都存成 `(1,3)`；
* 可以用这个规则来唯一标识一条“无向边”。

➡️ 方便后续 merge、join、对齐（比如匹配到 NBO 边表）。

---

#### （2）**传给 GNN 时复制反向边**

当你要把 NetworkX 图转成 PyG 的 `Data` 时，需要显式“双向展开”：

```python
edge_index = []
for u, v in G.edges():
    edge_index.append([u, v])
    edge_index.append([v, u])  # 加上反向边
edge_index = torch.tensor(edge_index).T
```

这样 PyG 模型（比如 GCN、GraphSAGE）能在消息传递时：

* 从 u 传到 v；
* 从 v 传回 u；
* 实现真正的“无向传播”。

---

### 🧭 举例：

| NetworkX 无向边 | 规范化 `(min,max)` | PyG edge_index（双向） |
| ------------ | --------------- | ------------------ |
| (3,1)        | (1,3)           | (1,3) & (3,1)      |
| (5,2)        | (2,5)           | (2,5) & (5,2)      |
| (0,4)        | (0,4)           | (0,4) & (4,0)      |

---

### 💡 一句话总结：

> “无向图的唯一表示靠 `(min(u,v), max(u,v))` 规范化，
> GNN 模型的双向传播靠 `(u,v)` 与 `(v,u)` 成对展开。”

