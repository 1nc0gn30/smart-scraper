"""
Reusable Python scraper & analyzer core.

Used by:
- FastAPI backend (main.py)
- Streamlit dashboard (streamlit-app/app.py)
- Potentially other consumers (CLI, notebooks, etc.)

Keeps all heavy lifting in pure Python.
"""

import os
import re
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlparse, quote_plus

import requests
from bs4 import BeautifulSoup
import pandas as pd

logger = logging.getLogger("scrape-bot.scraper")

SUPPORTED_MODES = ("url", "keyword")
SUPPORTED_TASKS = {
    "headlines": "Extract H1/H2/H3 headlines",
    "prices": "Find price-like values with context",
    "links": "Extract internal + external links",
    "summary": "Extract meaningful paragraphs",
    "meta": "Page title, meta description, Open Graph tags",
    "tables": "Extract HTML tables as structured data (pandas)",
}

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; StreamlitNetlifyCollab/2.0; +https://github.com/your-org)"
)
REQUEST_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}

# --- Core Fetch ---

def fetch_page(url: str, timeout: int = 18) -> str:
    """Fetch a page with polite headers. Raises on error."""
    if not url.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")

    resp = requests.get(
        url,
        headers=REQUEST_HEADERS,
        timeout=timeout,
        allow_redirects=True,
    )
    resp.raise_for_status()

    # Handle encoding
    if resp.encoding is None or resp.encoding.lower() in ("iso-8859-1", "ascii"):
        resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def fetch_search_results(query: str, max_results: int = 10, timeout: int = 15) -> List[Dict[str, str]]:
    """Perform a very lightweight DuckDuckGo HTML search scrape.
    Returns top organic result links. This is for demo purposes only.
    In production you would use official APIs or SerpApi etc.
    """
    q = quote_plus(query)
    search_url = f"https://html.duckduckgo.com/html/?q={q}"

    try:
        html = fetch_page(search_url, timeout=timeout)
        soup = BeautifulSoup(html, "html.parser")

        results = []
        for result in soup.select(".result")[:max_results]:
            a = result.select_one(".result__a")
            if not a or not a.get("href"):
                continue
            title = a.get_text(strip=True)
            # DuckDuckGo uses redirect URLs; the real url is in the result__url or we parse
            url_el = result.select_one(".result__url")
            href = a["href"]
            # Some results are //duckduckgo.com/l/?uddg=REAL_URL
            real_url = href
            if "uddg=" in href:
                # crude extraction
                try:
                    from urllib.parse import parse_qs, urlparse as up
                    qs = parse_qs(up(href).query)
                    real_url = qs.get("uddg", [href])[0]
                except Exception:
                    pass

            snippet_el = result.select_one(".result__snippet")
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""

            results.append({
                "title": title,
                "url": real_url,
                "snippet": snippet,
            })

        if not results:
            # Fallback: at least echo the query
            results.append({
                "title": f"Search for: {query}",
                "url": f"https://duckduckgo.com/?q={q}",
                "snippet": "No direct organic results parsed. Consider using a dedicated search API.",
            })
        return results
    except Exception as e:
        logger.warning("Search scrape failed: %s", e)
        return [{
            "title": f"Search results for '{query}'",
            "url": f"https://duckduckgo.com/?q={quote_plus(query)}",
            "snippet": "Live search temporarily unavailable in this demo. Try a direct URL instead.",
        }]


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def truncate(text: str, length: int = 280) -> str:
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "..."


# --- Individual Task Handlers (pure functions) ---

def handle_headlines(soup: BeautifulSoup, base_url: str, max_results: int) -> Dict[str, Any]:
    seen = set()
    items = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = clean_text(tag.get_text())
        if text and text not in seen:
            seen.add(text)
            items.append({"tag": tag.name.upper(), "text": text})
        if len(items) >= max_results:
            break
    return {
        "task": "headlines",
        "count": len(items),
        "headlines": items,
    }


def handle_prices(soup: BeautifulSoup, base_url: str, max_results: int) -> Dict[str, Any]:
    # Broad but practical price regex
    pattern = re.compile(
        r"(?i)(?:[$€£¥₹₽]|USD|EUR|GBP)?\s?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})"
    )
    seen = set()
    items = []
    for el in soup.find_all(["span", "div", "p", "strong", "b", "a", "li"]):
        text = clean_text(el.get_text())
        for m in pattern.finditer(text):
            value = m.group(0).strip()
            if value and value not in seen:
                seen.add(value)
                items.append({
                    "price": value,
                    "context": truncate(text, 160),
                })
        if len(items) >= max_results:
            break
    return {
        "task": "prices",
        "count": len(items),
        "prices": items,
    }


def handle_links(soup: BeautifulSoup, base_url: str, max_results: int) -> Dict[str, Any]:
    seen = set()
    items = []
    parsed_base = urlparse(base_url)

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        abs_url = urljoin(base_url, href)
        # Filter obvious noise
        if "google.com" in abs_url or "doubleclick" in abs_url:
            continue
        title = clean_text(a.get_text()) or clean_text(a.get("title") or "") or abs_url.split("/")[-1]
        key = (abs_url, title[:80])
        if key not in seen:
            seen.add(key)
            items.append({
                "title": title[:120],
                "url": abs_url,
                "domain": urlparse(abs_url).netloc,
            })
        if len(items) >= max_results:
            break

    return {
        "task": "links",
        "count": len(items),
        "links": items,
    }


def handle_summary(soup: BeautifulSoup, base_url: str, max_results: int) -> Dict[str, Any]:
    paragraphs = []
    for p in soup.find_all("p"):
        t = clean_text(p.get_text())
        if len(t) > 42:
            paragraphs.append(t)
        if len(paragraphs) >= max_results:
            break
    return {
        "task": "summary",
        "paragraph_count": len(paragraphs),
        "paragraphs": paragraphs[:max_results],
    }


def handle_meta(soup: BeautifulSoup, base_url: str, max_results: int = 20) -> Dict[str, Any]:
    def get_meta(name_or_prop):
        tag = soup.find("meta", attrs={"name": name_or_prop}) or \
              soup.find("meta", attrs={"property": name_or_prop})
        return clean_text(tag["content"]) if tag and tag.get("content") else None

    title = clean_text(soup.title.string) if soup.title and soup.title.string else ""
    description = get_meta("description") or get_meta("og:description") or ""
    og_image = get_meta("og:image") or get_meta("twitter:image")
    canonical = ""
    can = soup.find("link", rel="canonical")
    if can and can.get("href"):
        canonical = urljoin(base_url, can["href"])

    meta = {
        "title": title,
        "description": description,
        "og:title": get_meta("og:title"),
        "og:description": get_meta("og:description"),
        "og:image": og_image,
        "og:site_name": get_meta("og:site_name"),
        "canonical": canonical,
        "keywords": get_meta("keywords"),
    }
    # Filter out Nones
    meta = {k: v for k, v in meta.items() if v}

    return {
        "task": "meta",
        "count": len(meta),
        "meta": meta,
    }


def handle_tables(soup: BeautifulSoup, base_url: str, max_results: int) -> Dict[str, Any]:
    """Extract tables. Try pandas.read_html first for best structured data, fallback to manual."""
    tables_data = []
    html_str = str(soup)

    try:
        # pandas.read_html is excellent for this
        from io import StringIO
        dfs = pd.read_html(StringIO(html_str), flavor="bs4")
        for idx, df in enumerate(dfs[:max_results]):
            # Clean df
            df = df.dropna(how="all").dropna(axis=1, how="all")
            df = df.fillna("")
            records = df.to_dict(orient="records")
            tables_data.append({
                "table_index": idx,
                "rows": len(df),
                "columns": list(df.columns),
                "preview": records[:8],   # limited preview
                "full_csv_preview": df.head(20).to_csv(index=False)[:1500],
            })
    except Exception as e:
        # Manual fallback
        logger.info("pandas.read_html failed, falling back to manual extraction: %s", e)
        for idx, table in enumerate(soup.find_all("table")[:max_results]):
            rows = []
            headers = []
            thead = table.find("thead")
            if thead:
                headers = [clean_text(th.get_text()) for th in thead.find_all(["th", "td"])]
            for tr in table.find_all("tr")[:20]:
                cells = [clean_text(td.get_text()) for td in tr.find_all(["th", "td"])]
                if cells:
                    rows.append(cells)
            tables_data.append({
                "table_index": idx,
                "headers": headers,
                "sample_rows": rows[:5],
                "row_count_estimate": len(table.find_all("tr")),
            })

    return {
        "task": "tables",
        "count": len(tables_data),
        "tables": tables_data,
    }


TASK_HANDLERS = {
    "headlines": handle_headlines,
    "prices": handle_prices,
    "links": handle_links,
    "summary": handle_summary,
    "meta": handle_meta,
    "tables": handle_tables,
}


# --- Public API ---

def scrape_and_analyze(
    *,
    url: Optional[str] = None,
    query: Optional[str] = None,
    mode: str = "url",
    task: str = "headlines",
    max_results: int = 50,
    timeout: int = 18,
) -> Dict[str, Any]:
    """High level entrypoint. Returns a clean result dict.

    When mode="keyword", `query` is required and we perform search first.
    """
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported mode: {mode}")
    if task not in SUPPORTED_TASKS:
        raise ValueError(f"Unsupported task: {task}")

    result_base = {
        "mode": mode,
        "task": task,
        "max_results": max_results,
        "source": None,
    }

    if mode == "keyword":
        if not query or not query.strip():
            raise ValueError("query is required when mode=keyword")
        q = query.strip()
        result_base["query"] = q

        search_results = fetch_search_results(q, max_results=min(12, max_results))

        # For keyword mode we can either:
        # 1. Return the search results directly (great UX)
        # 2. Or follow first result and run the actual task.
        # We do both: always include "search_results", and if possible run the chosen task on first hit.

        result_base["search_results"] = search_results

        # Try to run the chosen task on the first usable result (best effort)
        first_url = None
        for r in search_results:
            if r.get("url") and r["url"].startswith("http"):
                first_url = r["url"]
                break

        if first_url and task != "meta":  # meta is less useful on search result page
            try:
                html = fetch_page(first_url, timeout=timeout)
                soup = make_soup(html)
                handler = TASK_HANDLERS.get(task)
                if handler:
                    task_data = handler(soup, first_url, max_results)
                    result_base.update(task_data)
                    result_base["source"] = first_url
                    result_base["analyzed_from_first_result"] = True
            except Exception as e:
                logger.info("Could not scrape first search result for task: %s", e)
                result_base["analyzed_from_first_result"] = False

        if "count" not in result_base:
            result_base["count"] = len(search_results)
        return result_base

    # --- URL mode ---
    if not url:
        raise ValueError("url is required when mode=url")

    result_base["url"] = url
    result_base["source"] = url

    html = fetch_page(url, timeout=timeout)
    soup = make_soup(html)

    handler = TASK_HANDLERS.get(task)
    if not handler:
        raise ValueError(f"No handler for task '{task}'")

    task_result = handler(soup, url, max_results)
    result_base.update(task_result)

    # Add a tiny bit of always-useful context
    page_title = clean_text(soup.title.string) if soup.title else ""
    if page_title:
        result_base["page_title"] = page_title

    return result_base


# Convenience: convert any result into a pandas DataFrame (for Streamlit, exports, etc)
def result_to_dataframe(result: Dict[str, Any]) -> Optional[pd.DataFrame]:
    task = result.get("task")
    if task == "headlines" and result.get("headlines"):
        return pd.DataFrame(result["headlines"])
    if task == "prices" and result.get("prices"):
        return pd.DataFrame(result["prices"])
    if task == "links" and result.get("links"):
        return pd.DataFrame(result["links"])
    if task == "summary" and result.get("paragraphs"):
        return pd.DataFrame({"paragraph": result["paragraphs"]})
    if task == "tables" and result.get("tables"):
        # Return first table preview
        first = result["tables"][0]
        if "preview" in first:
            return pd.DataFrame(first["preview"])
        return None
    if task == "meta" and result.get("meta"):
        return pd.DataFrame([result["meta"]])
    if result.get("search_results"):
        return pd.DataFrame(result["search_results"])
    return None
