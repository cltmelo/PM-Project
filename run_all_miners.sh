#!/bin/bash

# Multi-Miner Runner
# This script runs all available miners (AlphaMiner, GeneticMiner, InductiveMiner, SplitMiner)

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to run a miner
run_miner() {
    local miner=$1
    echo ""
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}    Running $miner${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo ""
    
    if [ -f "$miner/main.py" ]; then
        conda run -n process-mining python -m $miner.main
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ $miner completed successfully${NC}"
        else
            echo -e "${RED}❌ $miner failed${NC}"
        fi
    else
        echo -e "${RED}❌ $miner/main.py not found${NC}"
    fi
}

# Parse arguments
if [ $# -eq 0 ]; then
    # Run all miners
    echo -e "${BLUE}Running all available miners...${NC}"
    run_miner "AlphaMiner"
    run_miner "GeneticMiner"
    run_miner "InductiveMiner"
    run_miner "SplitMiner"
else
    # Run specific miners
    for miner in "$@"; do
        run_miner "$miner"
    done
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ All miners execution complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
