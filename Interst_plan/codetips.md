From installnotes.md
**在terminal还是notebook里跑安装代码**
## Terminal vs Notebook 的差异

装包用哪个环境就会装到哪个 Python 里。
终端里：python -m pip ... 会安装到当前 which python 指向的解释器。
Notebook 里：%pip install ... 会安装到当前内核的解释器。
你现在两边都指向 gnn_env，但仍然 Has TF? False，说明要么安装没有落到这个解释器的 site-packages，要么平台不满足 wheel 的生效条件（最常见是 macOS 版本偏低）。

## 在哪里跑、怎么跑
赶紧适应命令行 terminal是神
