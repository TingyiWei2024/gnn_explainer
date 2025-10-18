# 对怎么从txt里直接读取data到excel里的代码解析
-> 默认解析的对象是这些常量：正则表达式 （筛选出符合规则的子串）

## 1. 解读字符串
DEFAULT_PER_ATOM_REGEX = r"Atom\s+(\d+)\((\w)\s*\):\s*([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)“
-> 见2 正则表达式.md复习

## Q1 为什么放在文件最开头？
这其实是个代码设计上的好习惯，叫做 “常量集中定义” 或 “可配置参数上移”。
| 原因           | 解释                                                  |                                                                                                                                |
| ------------ | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 🧠 **可读性好**  | 一眼就能看出脚本默认匹配的文本格式是什么。读别人代码时非常直观。                    |                                                                                                                                |
| 🔧 **易于修改**  | 以后如果你的文本格式稍变（比如 `(Cl )`、`(Si )`），你只要改这一行，不需要在函数内部改。 |                                                                                                                                |
| 🧱 **可复用**   | 这个正则可以在多个函数中引用，不必每次重新写一遍。                           |                                                                                                                                |
| 🧩 **函数更通用** | 在函数里我们写了 `regex: Optional[str                       | Pattern] = None`，这表示“如果没传 regex 参数，就用 DEFAULT_PER_ATOM_REGEX”。 也就是：<br>`pattern = re.compile(regex or DEFAULT_PER_ATOM_REGEX)` |
| 🛡️ **防止错误** | 如果正则写错或者要调试，只改一处，不影响函数逻辑。                           |                                                                                                                                |


## 正则匹配
- pattern = re.compile(regex or DEFAULT_PER_ATOM_REGEX)
-> re.compile() 编译正则表达式的函数
-> 会把一个正则表达式 字符串（例如 "Atom\s+(\d+)"）
编译成一个 正则表达式对象（pattern object），
这样 Python 执行匹配时就会更快、更方便复用
-> 不用每次都重复调用字符串了
---
pattern = re.compile(r"Atom\s+(\d+)")
for line in lines:
    m = pattern.search(line)
---
这样做的好处：只编译一次；在循环或大文件处理中会快得多；
-> 后续多次使用时直接调用pattern object
pattern.search()、pattern.findall()、pattern.finditer()；

## 2. 读取文本并逐行匹配

### edge prase logic
The edge features capture bond-pair properties from the NBO/Multiwfn output.
They will represent each bond (src ↔ dst) in your molecular graph.
We already agreed the file will be edge_features.xlsx → sheet edges, with one row per bond and the following key rules:

1 molecule → many bonds.
→ We use mol_id to identify which molecule the bond belongs to.

Edges are undirected in storage.
→ Store each bond once with src < dst.
(If the model later needs directed edges, we’ll double them during graph construction.)

Indices correspond to RDKit atom indices after Chem.AddHs()
→ These align perfectly with your node Excel.