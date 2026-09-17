#!/bin/sh
# MEMS modeling web viewer — port 8971 (old modeling project uses 8941/8942)
cd "$(dirname "$0")" && exec python3 -m http.server 8971
