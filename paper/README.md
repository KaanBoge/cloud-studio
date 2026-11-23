# Cloud survival in supersonic winds

**[Read the paper (PDF)](Cloud_survival_OJA.pdf)** · **[Download the Overleaf project](Cloud_survival_OJA_Overleaf.zip)**

The manuscript compares twelve hydrodynamic methods for a cloud in a Mach 2 wind at a density contrast of 100, each at three resolutions (n = 32, 64 and 128), with additional grid calculations at contrasts of 10 and 1000. It includes a boundary control: Athena++ repeated in the two periodic domains used by the moving mesh and particle based methods. It uses the Open Journal of Astrophysics LaTeX class.

For Overleaf, upload the ZIP, choose `main.tex` as the main document and select XeLaTeX. The package includes the class, bibliography, figures, the saved dense mass histories and the plotting scripts. The compiled PDF is included for comparison.

The series, figure scripts and custom source code are also in [code/paper](../code/paper/), with the licence scope recorded in [repository licensing](../LICENSING.md). This folder contains reduced data and figures, not the raw simulation outputs.
