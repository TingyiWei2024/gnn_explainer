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


from .log files
Summary of Natural Population Analysis
## Natural Charge

To Multiwfn_3.8 encoding
9 Bond order analysis
## 9-1 Mayer bond order analysis
## 9-3 Wiberg bond order analysis in Lowdin orthogonalized basis
9-4 Mulliken bond order (Mulliken overlap population) analysis

 7 Population analysis and calculation of atomic charges
7-1  1 Hirshfeld atomic charge 
	-  Use build-in sphericalized atomic densities in free-states (more convenient)
7-5-1  Mulliken population analysis- Output Mulliken population and atomic charges
	- Population of basis functions
7-11-1  Atomic dipole corrected Hirshfeld atomic charge (ADCH) (recommended) 
	- Use build-in sphericalized atomic densities in free-states (more convenient)

