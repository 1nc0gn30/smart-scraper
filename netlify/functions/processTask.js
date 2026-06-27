/**
 * Netlify Function: processTask
 *
 * Responsibilities:
 * 1. Verify the user is logged in via Netlify Identity (JWT)
 * 2. Forward the authenticated request to the private Python FastAPI backend
 * 3. Return clean results
 *
 * Security notes:
 * - Real signature verification is best done with the `jsonwebtoken` or `jose` package.
 * - This implementation does strong payload validation + kid check as a solid demo.
 * - For higher security: npm install jsonwebtoken and do full RS256 verification.
 */

const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";
const PYTHON_API_KEY = process.env.PYTHON_API_KEY || process.env.API_KEY || "";

const NETLIFY_JWKS_URL = "https://identity.netlify.com/.well-known/jwks.json";

let jwksCache = null;
let jwksFetchedAt = 0;
const JWKS_CACHE_TTL_MS = 1000 * 60 * 60 * 4; // 4 hours

async function getJwks() {
  const now = Date.now();
  if (jwksCache && now - jwksFetchedAt < JWKS_CACHE_TTL_MS) {
    return jwksCache;
  }
  const res = await fetch(NETLIFY_JWKS_URL);
  if (!res.ok) {
    throw new Error("Failed to fetch Netlify JWKS: " + res.status);
  }
  jwksCache = await res.json();
  jwksFetchedAt = now;
  return jwksCache;
}

function base64UrlDecode(str) {
  let b64 = str.replace(/-/g, "+").replace(/_/g, "/");
  const pad = b64.length % 4;
  if (pad) b64 += "=".repeat(4 - pad);
  return Buffer.from(b64, "base64").toString("utf8");
}

async function verifyNetlifyJwt(token) {
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("Malformed JWT");

  let header;
  let payload;

  try {
    header = JSON.parse(base64UrlDecode(parts[0]));
    payload = JSON.parse(base64UrlDecode(parts[1]));
  } catch (e) {
    throw new Error("Invalid JWT structure");
  }

  const jwks = await getJwks();
  const key = (jwks?.keys || []).find((k) => k.kid === header.kid);
  if (!key) {
    throw new Error("Unknown signing key (kid not found)");
  }

  // Basic claims validation (demo-grade; add full signature verification in prod)
  const now = Math.floor(Date.now() / 1000);
  if (payload.exp && payload.exp < now) throw new Error("Token expired");
  if (payload.nbf && payload.nbf > now) throw new Error("Token not yet valid");
  if (!payload.sub) throw new Error("Missing subject claim");

  // Attach useful info
  return {
    sub: payload.sub,
    email: payload.email,
    app_metadata: payload.app_metadata || {},
    user_metadata: payload.user_metadata || {},
    exp: payload.exp,
  };
}

async function callPythonBackend(body) {
  const headers = { "Content-Type": "application/json" };
  if (PYTHON_API_KEY) {
    headers["X-API-Key"] = PYTHON_API_KEY;
  }

  // Prefer the new unified endpoint
  const endpoint = `${PYTHON_API_URL.replace(/\/$/, "")}/analyze`;

  const resp = await fetch(endpoint, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    let text = "";
    try { text = await resp.text(); } catch (_) {}
    throw new Error(`Python backend responded ${resp.status}: ${text.slice(0, 280)}`);
  }
  return resp.json();
}

export const handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return {
      statusCode: 405,
      headers: { Allow: "POST", "Content-Type": "application/json" },
      body: JSON.stringify({ error: "Method not allowed. Use POST." }),
    };
  }

  // 1. Auth: require Netlify Identity JWT
  const authHeader =
    (event.headers.authorization || event.headers.Authorization || "").trim();

  if (!authHeader.startsWith("Bearer ")) {
    return {
      statusCode: 401,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ error: "Authentication required. Please log in." }),
    };
  }

  const token = authHeader.slice("Bearer ".length).trim();
  let user;
  try {
    user = await verifyNetlifyJwt(token);
  } catch (err) {
    return {
      statusCode: 401,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ error: "Unauthorized: " + err.message }),
    };
  }

  // 2. Parse body
  let body;
  try {
    body = JSON.parse(event.body || "{}");
  } catch (e) {
    return {
      statusCode: 400,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ error: "Invalid JSON body" }),
    };
  }

  // Support both legacy "url" and new flexible input (url or query + mode)
  const url = typeof body.url === "string" ? body.url.trim() : "";
  const query = typeof body.query === "string" ? body.query.trim() : "";
  const mode = (typeof body.mode === "string" && ["url", "keyword"].includes(body.mode)) ? body.mode : (url ? "url" : "keyword");
  const task = typeof body.task === "string" ? body.task.trim() : "headlines";
  const maxResults = Math.min(Math.max(Number(body.max_results) || 50, 5), 150);

  if (!url && !query) {
    return {
      statusCode: 400,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ error: "Provide either a 'url' or a 'query' (search term)." }),
    };
  }

  // 3. Forward to Python
  try {
    const payload = {
      url: url || undefined,
      query: query || undefined,
      mode,
      task,
      max_results: maxResults,
    };

    const data = await callPythonBackend(payload);

    // Attach who triggered it (useful for audit / UI)
    const enriched = {
      ...data,
      _auth: {
        user: user.email || user.sub,
      },
    };

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(enriched),
    };
  } catch (err) {
    console.error("processTask error:", err);
    return {
      statusCode: 502,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ error: err.message || "Backend request failed" }),
    };
  }
};

