# Team Contributions & Task Distribution

This document outlines the operational contributions and the task distribution established by the development group for the Process Mining benchmarking project on the BPI Challenge 2017 dataset.

## 1. Workload & Task Distribution

To ensure absolute academic equity and balance throughout the semester, the core deliverables of this project were structurally decoupled into distinct engineering and operational tracks, with all four members contributing equally to the collaborative milestones:

* **Term Paper & Writing:** The conceptual framework, literature review, and experimental analysis were written collaboratively. Each member was responsible for documenting their respective process discovery paradigm in respective sections, while jointly refining the introduction, methodology, and GenAI reports.
* **Academic Poster Design:** The poster layout, core highlights, and visualization grids were developed through synchronized group sessions, ensuring a balanced presentation of text, metrics, and discovered outcomes.
* **Project Presentation Video:** The script formulation, editing, and final recording duties were divided uniformly, with each member presenting their core algorithmic focus and contribution on the ending.

---

## 2. Individual Contributions Breakdowns

### Ernesto Ulises Hernández Martínez
* **Primary Focus:** Implementation of the **Alpha Miner** (Baseline) and engineering of the **Centralized Comparison and Conformance Checking Framework**.
* **Key Deliverables:** Synthesized the Petri net outputs for the deterministic baseline.
    * Built the unified trace replay engine using alignment-based conformance utilities via the `pm4py` API to calculate required metrics for all models.
    * Contributed to the writing of sections corresponding to the baseline and framework results.
    * Handled final video coordination, editing, and repository validation checks.

### Lucas Corlete Alves de Melo
* **Primary Focus:** Implementation, hyperparameter optimization, and convergence analysis of the **Genetic Miner** optimization framework.
* **Key Deliverables:** Developed the multi-objective fitness function scoring systems (`WEIGHT_FITNESS = 0.7`, `WEIGHT_SIMPLICITY = 0.3`) and managed the 50-generation execution lifecycle scripts.
    * Exported the resulting optimized Petri net markup graphs and local JSON scoreboards.
    * Authored the technical portions of sections regarding to **Genetic Miner**, and handled the primary curation of the Appendix and GenAI logs.

### Matheus Hipolito Carvalho
* **Primary Focus:** Implementation, calibration, and evaluation of the **Split Miner** paradigm.
* **Key Deliverables:** Filtered infrequent behaviors and ruidoso paths within the Split Miner pipeline to generate clean graph representations.
    * Designed the unified layout theme, typography, and color palette alignment for the academic poster.
    * Co-developed the slide transitions and structure for the presentation video.

### Joao Moises Inga Gallo
* **Primary Focus:** Implementation, block-structuring calibration, and evaluation of the **Inductive Miner** paradigm.
* **Key Deliverables:** Fine-tuned noise thresholds within the inductive pipeline to ensure structural soundness and maximize model generalization marks.
    * Contributed the comparative text blocks for the Inductive Miner in the experimental section of the paper.
    * Handled final video coordination, compilation, and repository validation checks.

---

## 3. Verification Sign-off

By hosting this document within the public source tree alongside the execution artifacts, all members verify the accuracy of this distribution and confirm their equal share in the project's execution.