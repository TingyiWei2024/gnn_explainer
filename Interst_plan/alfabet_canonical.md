from work_notes 一.Q2

**-> 应该是源于rdkit最开始的基础库？有时间看看**
我帮你查了一下 “alfabet.fragment.canonicalize_smiles” 的背景和可能实现来源，下面是我的整理 +推论。可能不一定能完全确认（因为我没看到这个函数在公开源码里被明确标注为继承自 RDKit 的哪一部分），但我可以把靠谱的线索给你。

---

## 🔍 查到的线索

1. **ALFABET 项目简介**
   “ALFABET” 是一个 用于预测有机分子的键裂解能 (bond dissociation energy, BDE) 的机器学习 / 图神经网络工具包。这个库确实在其 GitHub 仓库里。([GitHub][1])
   在 README 里，它提到输入是 SMILES 字符串，然后内部会做一系列处理（包括构造分子图、切割键、分片等）来预测 BDE。([GitHub][1])

2. **在 ALFABET 里有 `canonicalize_smiles`**
   你说的代码片段 “from alfabet.fragment import canonicalize_smiles” 暗示 ALFABET 的子模块 `fragment` 里有这个函数。
   在 ALFABET 的 GitHub 仓库里（在 `NREL/alfabet`）可以查到项目结构。([GitHub][1])
   我在公开文档里没能直看到 `fragment/canonicalize_smiles` 的具体实现代码（至少不是在 README 或高层文档里）。

3. **RDKit 的 canonical SMILES 支持**
   在 RDKit 中，本身就有 canonical SMILES 的支持：有 `Chem.CanonSmiles(smi, useChiral=1)` 这个函数，可以把任意 SMILES 字符串 canonical（标准化）。([RDKit][2])
   也有 `MolToSmiles(mol, canonical=True)` 等接口（默认就是 canonical 模式）。([RDKit][3])

4. **不同工具的 canonical SMILES 算法不一定一致**
   这是化学信息学里大家都知道的一点：不同的 toolkit（如 Daylight、OpenBabel、RDKit、CDK 等）分别有各自的 canonical 算法（有时还会因版本不同而有微妙差别）。([en.wikipedia.org][4])
   所以，即便 ALFABET 是借助 RDKit，也可能在其 `canonicalize_smiles` 上加了一层封装或处理。

5. **ALFABET 用 RDKit**
   在 ALFABET 的 README 中，它建议安装 `rdkit` 作为依赖（因为 SMILES → 分子图构造、断键、分片等都可能用到 RDKit 的能力）。([GitHub][1])
   这说明 ALFABET 很可能在其内部使用 RDKit 的分子操作能力（比如 `Chem.MolFromSmiles`、`MolToSmiles`、分子图遍历、切割键等）。

---

## 🧩 我的推断：`canonicalize_smiles` 在 ALFABET 是怎么做的

综合上述线索，我认为 `alfabet.fragment.canonicalize_smiles` 很可能是一个 **对 RDKit 的封装 / 包装**，做一些额外处理后再调用 RDKit 的 canonical SMILES 功能。可能包括：

* 将输入 SMILES 用 RDKit 解析成 `Mol`（`Chem.MolFromSmiles`）
* 对一些异常或边界情况做清理、标准化（比如显式或隐式氢、立体化学、环标号重排序等）
* 最终调用 `Chem.MolToSmiles(mol, canonical=True, ...)` 或 `Chem.CanonSmiles(...)` 得到规范的 SMILES
* 可能还会把某些原子编号的映射关系、断键标识、片段连接点等做一些处理，以便后续 “fragment” 模块里使用

也就是说，`canonicalize_smiles` 应该不是 “完全从零自己写一个 canonical 算法” 的，而是依赖 RDKit 的能力 + 本身做一些预处理 / 后处理。

---

## 🧐 怎么进一步确认

如果你本地有 ALFABET 的源代码，你可以这样确认：

* 在你本地环境或克隆的 ALFABET 仓库中，打开 `alfabet/fragment/canonicalize_smiles.py` 或 `alfabet/fragment/__init__.py`，看其实现具体内容
* 检查这个函数内部是否 导入了 `rdkit.Chem` 等模块
* 看这个函数在极端输入上的表现，是否和直接 RDKit 的 `Chem.CanonSmiles()` 输出一致
* 若 ALFABET 的版本不同，有可能其封装做了些变动（如对氢、立体、断键符号等调整）

---

如果你愿意的话，我可以帮你在 ALFABET 的 GitHub 仓库里 **定位这个函数的源码**，看看它是怎么写的，你要吗？（我可以尝试查看 `NREL/alfabet` 仓库的代码）

[1]: https://github.com/NREL/alfabet?utm_source=chatgpt.com "NREL/alfabet: Machine learning predictions of bond ..."
[2]: https://www.rdkit.org/docs/source/rdkit.Chem.html?utm_source=chatgpt.com "rdkit.Chem package — The RDKit 2025.03.3 documentation"
[3]: https://www.rdkit.org/docs/GettingStartedInPython.html?utm_source=chatgpt.com "Getting Started with the RDKit in Python"
[4]: https://en.wikipedia.org/wiki/Simplified_Molecular_Input_Line_Entry_System?utm_source=chatgpt.com "Simplified Molecular Input Line Entry System"
