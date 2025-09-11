#!/usr/bin/env bash
# Zet -a aan om alle variabelen automatisch te exporteren
set -a
# Laad je lokale .env
[ -f .env ] && source .env
set +a
# Start Streamlit
streamlit run app.py
