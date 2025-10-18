# BDE
# 一. module input

## **Q1 为什么要导入RDKit / NetworkX / pandas，这几个库都是我们在运行数据转制输入时会常用的库吗？**
-> 三大基础库的“角色分工”
**RDKit 讲“化学与索引”，NetworkX 讲“图与属性”，pandas 讲“表与对齐”**

1. RDKit（化学层）
用来把 SMILES→分子对象，得到原子/键索引、拓扑、性质。
你可以把它当作“分子真相源”：
MolFromSmiles / AddHs / GetAtoms() / GetBonds()
-> 原子索引（0..N-1）、键两端 (u,v)、芳香性、价态等
➜ 我们依赖 RDKit 来定义节点/边集合与索引一致性。

2. NetworkX（图容器层）
轻量图数据结构（节点、边、属性），方便你先把BDE/BDfE 写进边属性、做验证/导出。
➜ 过渡态容器：从 RDKit 拿到“分子拓扑”，把 alfabet 的预测“贴”在边上，最后再转 PyG。

3. pandas（表格/中间产物层）
逐键 DataFrame 是 alfabet 的输出（start_atom, end_atom, bde_pred …），
你用它做 去重、合并、排序、对齐断言。
➜ 事实账本：任何图 ↔ 表的对齐，先在 pandas 里核对清楚再落到图。

**-->为什么要用表做对齐，直接插入进图里不好吗？在设计模型一开始就想的是先把smile变成图再插入数据成表还是先成表合并？（后面看完了再思考 先不展开 有时间问问）**
方便多项数据处理合并？所以alfabet的输出是一张表 所以是先架构矩阵对齐了再用nx卷？

---

## **Q2.关于alfabet:https://github.com/NREL/alfabet**
这是一个关于经过训练的图神经网络模型，用于预测含有 C、H、N 和 O 原子的有机分子的均裂键解离能 (BDE)的库，我们是直接调用的这个库来计算，但我们需要对这个库有哪些基本的认识和至少要掌握哪些基准点才能调用自如呢？ 
核心：Input/Output Contract
->  和外部库/脚本约好：输入是什么格式、输出长什么样、索引/单位怎么解释。
    这样上下游脚本才能无缝衔接，不至于对不上号。

->> alfabet 的 IO 契约
a. 输入（I）
一个 SMILES 字符串，最好是规范化后的（canonical）； # 同一个分子，只生成 唯一且标准化的 SMILES 表达式
我们建议用 canonicalize_smiles(smiles) 来得到这个“规范版”。 # or from rdkit.Chem.MolToSmiles import MolToSmiles
                                                       #    canonical = Chem.MolToSmiles(mol, canonical=True)

b. 输出（O）
一张 逐键的表（pandas DataFrame），至少含这些列：
start_atom、end_atom：整型索引（从 0 开始），表示断裂的两端原子；
bde_pred、bdfe_pred：预测的能量值（通常 kcal/mol）；
其它辅助列（如 fragment1/fragment2/molecule/...）。

**默认假设：start_atom/end_atom 与 RDKit（未加氢）的原子索引一一对应。-> 为什么要默认假设，我们用rdkit里chem模块Chem.MolFromSmiles解码后得到的id不应该是一致的吗，这个索引不久来自这函数运算完的结果吗？**
应该是alfabet是在没加h上训练的，所以我们默认按没加h的索引预测

为什么重要？
你后续要把这些列挂到图的边上；如果索引或单位错了，训练出来就全是噪音。
所以我们总是先写断言去“验明正身”。

B. 作用边界（什么能做 / 不能做）：
**只能做c/h/n/o的预测 用check_input检查** 
    can_smiles = canonicalize_smiles(smiles)
    is_outlier, missing_atom, missing_bond = check_input(can_smiles)

能做：对 C/H/N/O 的有机分子，给出均裂 BDE/BDfE 预测；覆盖常见 X–H、C–C、C–O…
不做：金属/卤素/硫…等元素域外，非常规电荷/自旋态、溶剂/温度效应、非常规键类型等
遇到域外：check_input 会给 outlier 信号；你要么过滤，要么降级处理。


C.再现性与版本
固定版本：alfabet==0.2.2（你脚本里已经 pin）
记录：alfabet.__version__、pip freeze，保证别人可以重跑

D.逻辑混乱点
千万别在构图那一步 AddHs()，否则原子总数变了 → start_atom/end_atom 全错位

**->> 再进一步：读它的 模型卡、训练数据域、误差分布，用于论文复现或方法改进**

---
## **Q3 这里的H是补齐了的吗？应该是没补齐的只有43行，应该有65才是完整的**
            # Step 2: add the H–X bond or update if it already exists
            # The heavy_idx is the integer from RDKit.
            if not G.has_edge(heavy_idx, h_node):
                G.add_edge(heavy_idx, h_node,
                           bond_index=bond_index_value,
                           bde_pred=bde_pred_value,
                           bdfe_pred=bdfe_pred_value)
            else:
                # If it somehow exists, just update attributes
                G[heavy_idx][h_node]['bde_pred'] = bde_pred_value
                G[heavy_idx][h_node]['bdfe_pred'] = bdfe_pred_value
                G[heavy_idx][h_node]['bond_index'] = bond_index_value


## Q4，进一步衍生的问题，在以后调用复现他人工作模型的时候，我应该至少掌握到哪种程度才能自如的调用开发自己的项目呢？
**->> 见future_power.md的讨论**
->我现在连l2都没达到吧呜呜

# 二. constract graph
## 1. 为什么用 NetworkX 保存？
- NetworkX 节点/边可以带任意键值对属性 → 调试友好（可导出表格做对齐检查）
- train前转成pyg的data: Data(x=[N, F_node], edge_index=[2, E], edge_attr=[E, F_edge], y=[N or M])
-> 这个就是我们gnn模型一直训练用的数据了

## 2. 怎么架构的这个模块：def create_bde_graph_selective_hs(smiles: str, bde_df) -> nx.Graph:

我的理解：
- 这是定义了一个将将计算出来的bde打包成图的函数，
-> 通过先congrdkit提取正确的smiles❌ **见Q2**
-> 然后以此为基准建立networkx图G “G = nx.Graph(mol=base_mol)”这行代码我不理解
->然后用atom.getindex和getbounds/输入正确的atom index/边的起止节点a1,a2到图里面作为节点/边的序数
->for循环应该是想通过heavy-hydrogen的区分方式确定要加的H键的位置和起止节点index 
->这里为什么在定义了s,e变量后就直接转到取bde算出来的值了
->同时这里其实没有加入bde计算的部分
->然后又开始判定这个算出来的bde两边的节点存不存在，存在就直接把bde预测值挂上去，不存在就用addH的逻辑加一个H的index再挂值

### Q1 def ... -> nx.Graph: 里的箭头是什么？
“-> nx.Graph”是类型提示（type hint），表示这个函数返回一个 networkx.Graph 对象。不影响运行，但能帮助读者和 IDE 理解 I/O 类型

### Q2 base_mol = Chem.MolFromSmiles(smiles)
字符串 SMILES → RDKit 的分子对象（未加氢）。这里默认你传进来的 smiles 已经是canonical（外部做的 canonicalize_smiles），函数本身不再规范化

### Q3 G = nx.Graph(mol=base_mol)
- 创建一个 NetworkX 无向图，并且把 base_mol（上一步里的rdkit分子对象） 作为图级属性存进去（键名 mol）。
- 这样以后需要时可以从 G.graph['mol'] 取回 RDKit Mol；
- 不参与节点/边结构，只是挂在图对象上的元数据。

### Q4 atom.getindex 和 getbonds…作为节点/边的序数
- 节点：用 atom.GetIdx()（0..N-1）作为节点 ID（整数）。
- 边：遍历 base_mol.GetBonds()，取两端 GetBeginAtomIdx() 与 GetEndAtomIdx()，作为边的两个端点。
- 先把所有重–重骨架写进图，边属性先占位（bde_pred=None 等）

### Q5 for 循环为什么直接取 bde_pred 值？它没算 BDE 吗？
-> 这个函数不计算 BDE，而是消费外部传入的 bde_df（由 predict_bdes 算好的结果）。
- 变量 s, e = row['start_atom'], row['end_atom'] 是 alfabet 给的**“这条键的两个端点索引”**；
- 再判断它们是重–重还是重–氢，据此更新/新增对应的图边，并把 bde_pred / bdfe_pred 挂到边属性上。
-> 重–重：骨架常常已有边 → 直接在该边更新属性；若确实骨架没有→ 新增边再写属性。
-> 重–氢：图里本来没显式氢，所以先造一个 'H_{hydrogen_idx}' 的氢节点，再连边并写属性。

## 3. 怎么架构def graph_to_df(bde_graph: nx.Graph) -> pd.DataFrame:
### 解构逻辑
- 这是为了单独检查图里的边属性，就把图摊平成表格拿出来看的函数；
-> 遍历graph里所有边
-> 把边的端点index提取出来
-> 要检查的数据取出来放表里 
-> nbo检查的时候可以调用

### Q1 怎么才架构好graph又要展开成dataframe？
- 方便人工对照检查 alfabet 的预测和图的挂接是否一致；
- 为后续可能的 merge / export / debug 提供清晰结构。
### Q2 和上面的函数有什么关系？
这个函数其实和前面的
create_bde_graph_selective_hs() 是镜像关系

| 函数                                | 输入             | 输出                     | 用途          |
| --------------------------------- | -------------- | ---------------------- | ----------- |
| `create_bde_graph_selective_hs()` | SMILES + BDE表  | **图 (`nx.Graph`)**     | “把 BDE 挂上图” |
| `graph_to_df()`                   | 图 (`nx.Graph`) | **表 (`pd.DataFrame`)** | “从图提取信息”    |

### Q3 为什么又单独定义一个bde_graph变量输入，不能直接用G吗？
- 变量名不重要，作用域才重要。
- G 是你在别处（比如 create_bde_graph_selective_hs 里）用的局部变量名；出了那个函数就不存在了。
- graph_to_df 是一个独立的小工具函数，它应该接收任意一个 NetworkX 图并把它摊平为表格——所以参数名写成 bde_graph、G、graph 都可以，本质一样。

-> 解耦与可复用。
单独定义参数而不是“偷用外部同名变量”，能让函数更通用、更好测试：你可以传入任何图（BDE 图、NBO 扩展后的图、子图等）都能转换。

### Q4 这里的节点为什么由变成了u和v，我们究竟是按哪个节点名称来的？
-> u / v 只是“边的两个端点”的局部变量名。
在 NetworkX 里遍历边时写 for u, v, data in G.edges(data=True) 是常见习惯：
- u 是边的一端，v 是另一端；

-> 它们不是重命名节点，只是把“这一条边连接的两个节点 ID”临时赋值给变量 u、v 方便读取。
-> 节点的“真正名字”就是你建图时用的节点 ID。
在你的图里：
- 重原子：节点名是 整数（0,1,2,…）来自 atom.GetIdx()；
- 氢：节点名是 字符串（比如 "H_-1", "H_102"）。
u 和 v 会是其中之一（可能是 int，也可能是 "H_*" 字符串）。
->无向边的顺序不保证。
因为图是无向的，G.edges(data=True) 迭代时得到 (u, v) 的先后顺序不固定。

## Q5 后面怎么调用的
1. 检查任意一个图边属性全进来没有
len(graph_to_df(graphs[0])) - graph_to_df(graphs[0]).isna().sum()
2. 常用df直接代替
df = graph_to_df(graphs[0])
print(df.columns)
3. 直接看表格常用code
graph_to_df(graphs[0])

# 三. 导入数据调用函数计算成图
output：
a. dfs → 存放每个分子的 bde_df（逐键预测表）；
b. graphs → 存放每个分子的 bde_graph（NetworkX 图）

## 1. urllib.parse 是啥？为啥在这个位置导入？
-> 把 molecule 列（即 canonical SMILES 字符串）转换成 URL 安全形式，用于后续在浏览器或 Notebook 输出时，生成可以点击的链接（比如绘图或 alfafet 可视化）
-> 能直接输出字符串形势的smiles确认graph架构成功没有
-> 为 DataFrame 添加一个新的列（smiles_link），方便后续分析或点击查看

bde_df['smiles_link'] = bde_df.molecule.apply(quote)

## 2. 用for循环计算分子并成图
- 统一检查提取smiles分子 
-> 用predict_bdes算出bde/bdfe的值放进bde_df表里
-> 去重？
    bde_df.drop_duplicates(['fragment1', 'fragment2']).reset_index(drop=True)
        → alfabet 可能对同一断裂片段预测了多次（比如两个不同 conformer）。
        → 去掉重复键，只保留唯一键
-> 出图调用前面create函数
- 把该分子的 BDE 预测结果 (bde_df) 与 RDKit 骨架 (can_smiles) 对齐
- 构建一个带属性的 NetworkX 图：
        节点：重原子 + 按需添加的氢；
        边属性：bde_pred, bdfe_pred, bond_index
-> 把图回填到 DataFrame
-> 循环不断添加算出来的分子的bde到dfs大表里

### Q1 学习bde_df['nx_graph'] = [bde_graph] * len(bde_df)
-> 在 DataFrame 的每一行新增一列 nx_graph，
    每一行的值都指向同一个图对象 bde_graph。 
1. bde_df['nx_graph']:在 pandas DataFrame 里创建一个新列，名字叫 "nx_graph"

2. [bde_graph] * len(bde_df) 创建的并不是多个独立副本，而是多个对同一对象的引用
* [bde_graph] → 建立一个只包含 一个元素（当前图对象）的列表；
* len(bde_df) → 把这个列表“复制”若干次，使它的长度与 DataFrame 行数相同
-> 列出每行属性对应的分子图

# 四 打包+ 测试验证读取
1. 打包
pickle 是 Python 内置的序列化库。
它可以把任何 Python 对象（字典、列表、自定义类、NetworkX 图）
→ 转成二进制字节流保存到磁盘；
也能反向“解包”回来

f"gpickle_graph_{idx}.pkl"
-> 动态生成文件名
pickle.dump(graph, f, pickle.HIGHEST_PROTOCOL)
把对象 graph 转成二进制字节流写入文件。HIGHEST_PROTOCOL 表示使用最高版本的压缩与效率。

2.测试读取
G = nx.path_graph(4)
with open('test.gpickle', 'wb') as f:
    pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)

with open('test.gpickle', 'rb') as f:
    G = pickle.load(f)
    
这部分是一个 测试段（sanity check），
用一个非常简单的图 nx.path_graph(4) 检查：
> `pickle.dump()` 是“冷冻保存对象”；
> `pickle.load()` 是“解冻恢复对象”。
> 它保证你在下一个脚本中直接获得完整的 NetworkX 图（含属性），
> 无需重跑 alfabet、RDKit、BDE 预测的全过程。



---
---


# NBO
# 一. model input
## Q1 应该怎么设置输入列表，最少都应该含有哪些columns，每个features名字应该怎么简称
-> 见node_features.md

## Q2 怎么从gaussion和multiwfn的文件里直接把要的结果读取到excel对应列里面
-> **见catch-data.md 的讨论，之后有时间了解了解**

## Q3 从.txt里提取
-> 见nbo_txtcatch.md and fold C24_results

## Q4 use random value to assum dataset input
