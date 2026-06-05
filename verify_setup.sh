#!/bin/bash

# Verification script for Process Mining setup

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Process Mining Setup Verification     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Check 1: Conda environment exists
echo -n "Checking process-mining environment... "
if conda env list | grep -q "process-mining"; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
fi

# Check 2: Python executable
echo -n "Checking Python executable... "
if [ -x "/opt/anaconda3/envs/process-mining/bin/python" ]; then
    echo -e "${GREEN}✅${NC}"
    PY_VERSION=$(/opt/anaconda3/envs/process-mining/bin/python --version)
    echo "   └─ $PY_VERSION"
else
    echo -e "${RED}❌${NC}"
fi

# Check 3: pm4py installation
echo -n "Checking pm4py installation... "
if /opt/anaconda3/envs/process-mining/bin/python -c "import pm4py; print(pm4py.__version__)" 2>/dev/null | grep -q "2.7"; then
    PM_VERSION=$(/opt/anaconda3/envs/process-mining/bin/python -c "import pm4py; print(pm4py.__version__)")
    echo -e "${GREEN}✅${NC}"
    echo "   └─ Version: $PM_VERSION"
else
    echo -e "${RED}❌${NC}"
fi

# Check 4: Other dependencies
echo -n "Checking pandas... "
if /opt/anaconda3/envs/process-mining/bin/python -c "import pandas" 2>/dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
fi

echo -n "Checking graphviz... "
if /opt/anaconda3/envs/process-mining/bin/python -c "import graphviz" 2>/dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
fi

# Check 5: Project structure
echo -n "Checking project structure... "
if [ -d "AlphaMiner" ] && [ -d "GeneticMiner" ] && [ -d "InductiveMiner" ] && [ -d "SplitMiner" ]; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
fi

# Check 6: Scripts
echo -n "Checking run scripts... "
if [ -x "run.sh" ] && [ -x "run_all_miners.sh" ]; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
fi

# Check 7: Requirements file
echo -n "Checking requirements.txt... "
if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Quick Command Reference               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Single Miners:${NC}"
echo "  pm_alpha        - Run AlphaMiner"
echo "  pm_genetic      - Run GeneticMiner"
echo "  pm_inductive    - Run InductiveMiner"
echo "  pm_split        - Run SplitMiner"
echo ""
echo -e "${YELLOW}All Miners:${NC}"
echo "  pm_all          - Run all miners"
echo ""
echo -e "${YELLOW}Environment:${NC}"
echo "  pm_activate     - Activate process-mining env"
echo "  conda run -n process-mining python -m AlphaMiner.main"
echo ""
echo -e "${GREEN}Setup verification complete!${NC}"
