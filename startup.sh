#!/bin/bash
# Azure App Service start command (port 8000 is what Azure forwards to)
python -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0
