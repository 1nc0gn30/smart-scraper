#!/bin/bash
# Quick CLI deploy helper for StreamlitNetlifyCollab
# Usage:
#   ./deploy-cli.sh netlify
#   ./deploy-cli.sh backend

set -e

echo "🚂 StreamlitNetlifyCollab CLI Deploy Helper"

case "$1" in
  backend)
    echo "=== Deploying FastAPI backend to Railway ==="
    if ! command -v ~/.railway/bin/railway &> /dev/null; then
      echo "Installing Railway CLI..."
      curl -fsSL https://railway.app/install.sh | sh
    fi

    cd python-backend
    echo "Logging into Railway..."
    ~/.railway/bin/railway login
    echo "Deploying backend..."
    ~/.railway/bin/railway up
    echo ""
    echo "✅ Backend deployed!"
    echo "  Check URL:   ~/.railway/bin/railway status"
    echo ""
    echo "Set variables (in Railway dashboard or CLI):"
    echo "  API_KEY=your-strong-secret"
    echo "  ALLOWED_ORIGINS=https://your-netlify-site.netlify.app"
    ;;

  netlify)
    echo "=== Deploying to Netlify via CLI ==="
    netlify login
    netlify init
    echo "Setting environment variable (you will be prompted for the backend URL)..."
    netlify env:set PYTHON_API_URL
    echo "Deploying to production..."
    netlify deploy --prod
    echo "✅ Done! Your site should be live."
    ;;

  streamlit)
    echo "=== Deploying Streamlit app (Railway example) ==="
    if ! command -v ~/.railway/bin/railway &> /dev/null; then
      curl -fsSL https://railway.app/install.sh | sh
    fi
    echo "Deploying streamlit-app/ ..."
    ~/.railway/bin/railway up --service streamlit-app || ~/.railway/bin/railway up
    echo "✅ Streamlit deployed (or link an existing project)"
    ;;

  *)
    echo "Usage: $0 [backend|netlify|streamlit]"
    echo ""
    echo "  backend   → Deploy FastAPI backend to Railway"
    echo "  netlify   → Deploy frontend + functions (Netlify)"
    echo "  streamlit → Deploy Streamlit dashboard"
    ;;
esac