# Quick Reference - Compare Framework Commands

## 🚀 Essential Commands

### From: `/Users/ernestou/Desktop/HOF/Process_Mining/PROJECT/PM-Project`

```bash
# Full comparison (recommended first run)
python -m Compare.main

# Safe test (no computation)
python -m Compare.main --dry-run

# Use existing outputs only (fast)
python -m Compare.main --no-run

# Force fresh run of all algorithms
python -m Compare.main --force

# Help menu
python -m Compare.main --help
```

## 📊 View Results

```bash
# See all generated files
ls -la compare/output/

# View text comparison table
cat compare/output/comparison_table.txt

# View comparison summary
cat compare/output/executive_summary.txt

# View CSV for Excel
cat compare/output/comparison_data.csv
```

## 📖 Read Documentation

```bash
# Complete usage guide
cat COMPARISON_GUIDE.md

# Detailed fixes and errors
cat COMPARE_FRAMEWORK_FIXES.md
```

## ⚙️ Modify Configuration

Edit: `Compare/config.py`

Common settings:
```python
event_log_path = "BPI Challenge 2017_1_all/BPI Challenge 2017.xes.gz"
output_dir = "compare/output"
generate_charts = True  # Enable/disable chart generation
chart_dpi = 150         # Chart resolution
```

## 🎯 Typical Workflow

```bash
# 1. Test setup
python -m Compare.main --dry-run

# 2. Run comparison
python -m Compare.main

# 3. Check results
ls -la compare/output/

# 4. View summary
cat compare/output/comparison_table.txt
cat compare/output/executive_summary.txt

# 5. Open HTML report (open in browser)
open compare/output/comparison_report.html
```

## 📊 Compared Algorithms

- **Genetic Miner** → `GeneticMiner/Output/`
- **Alpha Miner** → `AlphaMiner/output/` ✅ (complete)
- **Inductive Miner** → `InductiveMiner/Output/`
- **Split Miner** → `SplitMiner/Output/`

## ⏱️ Estimated Run Times

- Dry run: 5-10 seconds
- No-run: 10-30 seconds
- Full comparison: 30+ minutes (depends on algorithms)

## ❌ Troubleshooting

**"No data to compare"**
→ Run algorithms first, then `python -m Compare.main`

**"File not found"**
→ Check `Compare/config.py` for correct paths

**"Missing required files"**
→ Ensure algorithms output to expected directories

## 📁 Output Files

Generated in `compare/output/`:
- `comparison_table.txt` - Text format
- `comparison_table.html` - Interactive
- `comparison_data.csv` - Excel format
- `*.png` - 4 comparison charts
- `*.html` - HTML reports
- `*.md` - Markdown summary

---

**Status**: ✅ All errors fixed | Ready to use | Fully tested
