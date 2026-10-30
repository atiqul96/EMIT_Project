#!/bin/bash
# One-time deploy to Azure App Service. Run from inside the project folder after `az login`.
# Change APP to something globally unique (it becomes https://APP.azurewebsites.net)
APP=keystroke-auth-tonmoy
RG=keystroke-rg
LOC=southeastasia

az group create -n $RG -l $LOC
az webapp up -n $APP -g $RG -l $LOC --runtime "PYTHON:3.11" --sku B1
az webapp config set -n $APP -g $RG --web-sockets-enabled true \
  --startup-file "python -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0"
az webapp config appsettings set -n $APP -g $RG --settings TURSO_DATABASE_URL=$TURSO_DATABASE_URL TURSO_AUTH_TOKEN=$TURSO_AUTH_TOKEN
az webapp restart -n $APP -g $RG
echo "Open: https://$APP.azurewebsites.net"
