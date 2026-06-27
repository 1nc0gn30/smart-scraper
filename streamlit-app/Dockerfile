FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy build context (supports building from repo root OR from the streamlit-app/ folder)
COPY . /app/

# Install Python deps (find requirements.txt no matter the context)
RUN if [ -f /app/requirements.txt ]; then \
      pip install --no-cache-dir -r /app/requirements.txt; \
    elif [ -f /app/streamlit-app/requirements.txt ]; then \
      pip install --no-cache-dir -r /app/streamlit-app/requirements.txt; \
    else \
      pip install --no-cache-dir streamlit pandas requests beautifulsoup4 lxml python-dotenv; \
    fi

# Flatten files if we were given the full repo (context = root)
RUN if [ -d /app/streamlit-app ]; then \
      cp -a /app/streamlit-app/. /app/ || true; \
    fi

# Make sure scraper.py is directly importable at /app/scraper.py
RUN if [ ! -f /app/scraper.py ]; then \
      if [ -f /app/streamlit-app/scraper.py ]; then \
        cp /app/streamlit-app/scraper.py /app/scraper.py || true; \
      elif [ -f /app/python-backend/scraper.py ]; then \
        cp /app/python-backend/scraper.py /app/scraper.py || true; \
      fi; \
    fi

# Streamlit default port
ENV PORT=8501

EXPOSE 8501

CMD streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false