# frontend
Netlify SPA plus Netlify Function auth proxy.
## Local
```bash
# from repo root
PYTHON_API_URL=http://localhost:8000 PYTHON_API_KEY=*** netlify dev
```
## Deploy
`netlify deploy --prod` from repo root. Set PYTHON_API_URL and PYTHON_API_KEY in site env.
