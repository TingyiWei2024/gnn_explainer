## 10.13
1. from alfabet.drawing import draw_mol_outlier
这格代码跑了7个多小时了，没办法复现bde成图的脚本了，为啥import不进来呢？
-> 我们用的alfabet是改过的alfabet—lite,不是原库
-> 对的话，你需要卸载掉你的alfabet，卸载干净；装alfabet-lite

2.我们git在什么时候需要建分支？Í
-> gpt problem?

3. 我们怎么知道选的这个smiles呀?
4. 确定alfabet的IO我是否理解正确：
alfabet IO
输入：can_smiles = canonicalize_smiles(smiles) # 20 Molecules
输出表：predict_bdes(smiles) 
→ 列含 u(start_atom)/v(end_atom/)bde_pred/bdfe_pred/bond_index
索引：与 Chem.MolFromSmiles(s_can)（未加氢）的原子索引一致
单位：bde_pred/bdfe_pred 通常 kcal/mol

5. 我们bde的图里H是不全的，只补了需要算得部分的H，重复的H没加进图里，以C23为例少了20个H的样子
-> 还是确认一下下：alfabet是在没加h上训练的，所以我们默认按没加h的索引预测
->我们单列出bde/nbo分开做项目 在模型上可对比性应该相差不大？我评估不确定啦，峤哥你觉得呢？
-> again bde和nbo在h索引的处理上是完全不一样的，我好像找到接不上口的根本原因了

---

## 10.14
A1. 安装alfabet-lie from: https://github.com/kangqiao-ctrl/alfabet_lite
-> 详见installnotes.md
-> Q1. 安装TF用terminal操作还是notebook好？看下gpt的回答对不
--> terminal是神
**->> Q2.大问题 alfabet-lite里面没有canonicalize_smiles，我要用是像脚本里样又在环境里重新装alfabet0.2.2(这样不就重复了吗？)还是直接调用rdkit，急需建议❗️❗️❗️**

**3. 关于为啥需要改alfabet里的代码，看眼gpt的理解对不**
->是不是因为alfabet framgement和draw脚本l里用的是端点名字不一样start_atom? 
->而我们脚本里create_bde_graph_selective_hs用的是a1. a2 
->我觉得应该以create_graph这个函数里的为准统一成a1.a2，

gpt：
以构图函数为准：create_bde_graph_selective_hs 内部对 RDKit 骨架边用的是 a1, a2（来自 bond.GetBeginAtomIdx()/GetEndAtomIdx()），这代表骨架的重–重边。
图转表（graph_to_df）与所有“对外导出/对齐”的列名统一成 u, v（通用的“边端点”命名）。
alfabet / alfabet-lite 的逐键预测表统一使用 start_atom, end_atom（表示“要写入的那条键的两端”）。
也就是说：
外部来源（预测结果）：start_atom, end_atom
内部骨架（RDKit 遍历）：a1, a2（只在函数内部使用）
对外导出/巡检/merge：u, v
这样分层最清晰：外部（start/end）→ 内部（a1/a2）→ 导出（u/v）

**4.我们的图是无向图，pyg是有向图，我之前接口nbo脑子里没有这个概念**
edge_index = tensor([u1, u2])的问题，是不是有可能是我报错的原因呢？
标记一下，明天做nbo导入成图得特别注意一下