#!/bin/bash
# Install Google Gemini CLI globally via npm
# Requires Node.js >= 18

set -e

if ! command -v node &>/dev/null; then
  echo "Node.js is required. Please install Node.js >= 18 first."
  exit 1
fi

npm install -g @google/gemini-cli

echo "Gemini CLI installed: $(gemini --version)"
