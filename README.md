# Smart Scraper

Production-ready Netlify + FastAPI + Streamlit workflow.

- Frontend: https://lustrous-mandazi-dc139a.netlify.app
- Backend: https://reliable-courage-production-894f.up.railway.app
- Streamlit: https://streamlit-app-production-5cf0.up.railway.app

## Stack

- Netlify for frontend + identity + function proxy
- FastAPI for scraping + pandas analysis
- Streamlit as an optional companion dashboard

## Quick start

```bash
# backend
cd python-backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# frontend
netlify dev

# streamlit
cd streamlit-app && pip install -r requirements.txt
streamlit run app.py
```

## Env

See `.env.example`, `python-backend/.env.example`, and `frontend/.env.example`.

## Repos

- Remote: https://github.com/1nc0gn30/smart-scraper.git