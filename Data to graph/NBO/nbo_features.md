# NBO caiculation
## input SMILES
-> 含有完整原子的mol Chem.MolFromSmiles + Chem.AddHs

-> EmbedMolecule 为分子生成一个三维构象（从 SMILES 推出可能的 3D 坐标）
-> MMFFOptimizeMolecule MMFF94 力场（分子力场） 优化分子几何结构，使原子间距离、键角合理
-> 分子获得一个物理合理的初始几何，用于 DFT/NBO 输入

-> 将现有mol结构写入gjf文件方便gaussian提取计算
-> **解出每个原子的序列index:conf.GetAtomPosition(atom.GetIdx())**

### To gaussian/g16.b01
#p B3LYP/6-31G(d) Opt # dft优化结构的算子
#n B3LYP/6-311+G(2d,p) POP=NBO Geom=Checkpoint #nbo计算

### SSH nibi
-> #SBATCH --time=00-08:00  时间要久一点
-> 得将nbo.chk转成fchk才能输入到Multiwfn
- module load gaussian/g16.b01
- command -v formchk
- **for f in *-nbo.chk; do [ -f "$f" ] || continue; formchk "$f" "${f%.chk}.fchk"; done**
->我们需要的是.log和-nbo.fchk

# NBO features
from .log files
Summary of Natural Population Analysis
## Natural Charge -> **NodesF 1**

To Multiwfn_3.8 encoding
# 9 Bond order analysis
## 9-1 Mayer bond order analysis：
- bonder orders with absolute value ->**EdgesF 1**
- Total valences and free valences defined by Mayer -> **NodesF 2**

## 9-3 Wiberg bond order analysis in Lowdin orthogonalized basis
- Wiberg bond order -> **EdgesF 2**

## 9-4 Mulliken bond order (Mulliken overlap population) analysis
- bond order -> **EdgesF 3**

# 7 Population analysis and calculation of atomic charges
## 7-1  1 Hirshfeld atomic charge 
	->  Use build-in sphericalized atomic densities in free-states (more convenient)
- atom charges. -> **NodesF 3**

## 7-5-1  Mulliken population analysis- Output Mulliken population and atomic charges
	-> Population of basis functions
- population -> **NodesF 4**
- net charge -> **NodesF 5**

## 7-11-1  Atomic dipole corrected Hirshfeld atomic charge (ADCH) (recommended) 
	-> Use build-in sphericalized atomic densities in free-states (more convenient)
- atom charges -> **NodesF 6**

## 7-12-1 CHELPG ESP fitting atomic charge
- Charge -> **NodesF 7**

# NBO excel build
1. molecules.csv
-> SMILES和mol_id映射表

2. node_features.xlsx
-> columns: mol_id / atom_idx / element / features
		e.g.C24 / 1 / C&H /  
-> node_features:
q_npa — Natural charge (NPA) C24-ChargeFlog
val_mayer_tot — Mayer total valence 9-1
q_hirsh — Hirshfeld atomic charge 7-1
pop_mull — Mulliken population (basis-function population) 7-5-4
q_mull — Mulliken net atomic charge 7-5-4
q_adch — Atomic Dipole-Corrected Hirshfeld charge (ADCH) 7-11
q_chelpg — CHELPG charge 7-12

3. edge_features.xlsx
-> columns: mol_id / src, dst / bond_idx/ features
		e.g.C24 / 1,24 / / 
-> edge_features
bo_mayer_abs — Mayer bond order (absolute value) 9-1
bo_wiberg — Wiberg bond order ( Löwdin basis ) 9-3
bo_mull — Mulliken bond order (overlap population) 9-4

---
4. catch text results in excel