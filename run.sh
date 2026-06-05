#!/bin/bash

# AlphaMiner Pipeline Runner
# This script activates the process-mining conda environment and runs the AlphaMiner pipeline

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    AlphaMiner - Process Discovery${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if process-mining environment exists
echo -e "${YELLOW}Checking for process-mining conda environment...${NC}"
if ! conda env list | grep -q "process-mining"; then
    echo -e "${YELLOW}❌ process-mining environment not found!${NC}"
    echo "Creating process-mining environment..."
    conda create -n process-mining python=3.13 -y
    echo "Installing dependencies..."
    conda run -n process-mining pip install -r requirements.txt
    echo ""
fi

echo -e "${GREEN}✅ Activating process-mining environment...${NC}"
echo ""

# Run the pipeline
echo -e "${GREEN}Running AlphaMiner pipeline...${NC}"
echo ""

conda run -n process-mining python -m AlphaMiner.main

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Pipeline execution complete!${NC}"
echo -e "${GREEN}========================================${NC}"
