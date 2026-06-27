# python-backend
FastAPI backend for Smart Scraper providing `/analyze` and `/scrape`.
## Local
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
## Deploy
Railway/DockerFile or Render via render.yaml. Set API_KEY and ALLOWED_ORIGINS.
