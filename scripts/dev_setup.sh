#!/usr/bin/env bash
# Asterfusion CLI (v2) - Developer Environment Setup Script
# This script initializes a local development environment.
# Run this from the root of the repository: ./scripts/dev_setup.sh

# Exit immediately if a command exits with a non-zero status
set -e

# Terminal colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}[*] Starting Asterfusion CLI Dev Setup...${NC}"

# 1. Ensure we are in the project root
if [[ ! -f "pyproject.toml" ]]; then
    echo -e "${RED}[!] pyproject.toml not found. Please run this script from the project root:${NC}"
    echo -e "    ./scripts/dev_setup.sh"
    exit 1
fi

# 2. Check Python availability (requires 3.10+)
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[!] python3 could not be found. Please install Python 3.10 or higher.${NC}"
    exit 1
fi

echo -e "${BLUE}[*] Creating Python virtual environment (.venv)...${NC}"
python3 -m venv .venv

# 3. Activate the virtual environment
# Note: Since this runs in a subshell, we source it here to install dependencies, 
# but the user will still need to source it in their own terminal later.
source .venv/bin/activate

echo -e "${BLUE}[*] Upgrading pip...${NC}"
pip install --upgrade pip

echo -e "${BLUE}[*] Installing asterfusion-cli in editable mode with [dev] dependencies...${NC}"
# This reads the pyproject.toml and installs the CLI, plus dev tools (pytest, etc.)
pip install -e ".[dev]"

# 4. Scaffold configuration and runtime directories
echo -e "${BLUE}[*] Setting up local configuration and runtime folders...${NC}"

# Ensure runtime directories exist
mkdir -p logs
mkdir -p config/command_map

if [[ ! -f ".env" ]]; then
    echo -e "    -> Creating .env from template..."
    cp .env.example .env
else
    echo -e "    -> ${YELLOW}.env already exists, skipping.${NC}"
fi

if [[ ! -f "config/inventory.yaml" ]]; then
    echo -e "    -> Creating config/inventory.yaml from template..."
    cp config/inventory.yaml.example config/inventory.yaml
else
    echo -e "    -> ${YELLOW}config/inventory.yaml already exists, skipping.${NC}"
fi

# 5. Success Message
echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN} Setup Complete! ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "To start using the CLI, activate your virtual environment:"
echo -e "  ${YELLOW}source .venv/bin/activate${NC}"
echo -e ""
echo -e "Then, you can launch the shell from anywhere by typing:"
echo -e "  ${YELLOW}aster-cli${NC}"
echo -e ""
echo -e "Don't forget to update your credentials in the ${YELLOW}.env${NC} file!"
echo -e "======================================================"