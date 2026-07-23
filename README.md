# smart-scraper

Smart Scraper built with netlify, streamlit, and railway. Open to fork

## Overview
Smart Scraper built with netlify, streamlit, and railway. Open to fork

## Tech Stack
- Netlify (deployed)

## Project Structure
```
smart-scraper/
  - frontend
  - netlify
  - python-backend
  - streamlit-app
  (29 files total)
```

## Getting Started

### Prerequisites
- Node.js (v18+)
- npm or yarn

### Installation
```bash
git clone https://github.com/1nc0gn30/smart-scraper.git
cd smart-scraper
npm install
```

### Development
```bash
npm run dev
```

### Build
```bash
npm run build
```

### Available Scripts
  npm run dev - netlify dev
  npm run build - echo 'No build step for static frontend'

## Original README
<details>
<summary>Click to expand original README</summary>

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

</details>

## TODO / Roadmap
- [ ] Add unit tests
- [ ] Add LICENSE file
- [ ] Add Dockerfile for containerized deployment
- [ ] Add CI/CD pipeline
- [ ] Add contribution guidelines (CONTRIBUTING.md)
- [ ] Improve error handling and edge cases
- [ ] Add environment variable documentation
- [ ] Update dependencies to latest versions
- [ ] Add code comments and inline documentation

## Deployment
This project is deployed on Netlify. See netlify.toml for configuration.

## Author
**Neal Frazier** - [@AshAmplifies](https://github.com/1nc0gn30)

## Links
- GitHub: https://github.com/1nc0gn30/smart-scraper

---
*This README was enhanced as part of the neals-projects-2026 batch update.*
