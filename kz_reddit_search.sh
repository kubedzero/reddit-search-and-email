#!/bin/bash
# https://vaneyckt.io/posts/safer_bash_scripts_with_set_euxo_pipefail/
set -euo pipefail

# Script to assist with running the search in Cron (no built-in scheduler used)

# Move to the directory housing the Python code
cd "/root/reddit-search-and-email"

# Using python3, call search_runner.py with the necessary args
/root/.local/bin/pipenv run python3 "/root/reddit-search-and-email/search_runner.py" --onerun --config "/root/reddit-search-and-email/kz_config.json"