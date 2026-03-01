
# 🔗 URL Shortener with Analytics

A production-grade URL shortening service built with FastAPI, PostgreSQL, and Redis. Supports custom short codes, click analytics, caching, and rate limiting.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Analytics](#analytics)
- [Rate Limiting](#rate-limiting)
- [Database Schema](#database-schema)
- [Caching Strategy](#caching-strategy)
- [Development Tools](#development-tools)
- [Stretch Goals](#stretch-goals)

---

## Features

- **Shorten URLs** — Generate a random or custom short code for any URL
- **Redirect** — Visit a short URL and get redirected to the original
- **Expiry** — Set an optional expiry date on any short URL
- **Soft Delete** — Deactivate URLs without losing click history
- **Analytics** — Track clicks by day, browser, OS, and referrer
- **Redis Caching** — Popular URLs served from memory, not the database
- **Rate Limiting** — Per-IP request limits to prevent abuse

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| ORM | SQLAlchemy 2.0 |
| Validation | Pydantic v2 |
| Server | Uvicorn |
| Containerization | Docker + Docker Compose |

---

## Architecture

```
Incoming Request
      ↓
Rate Limiter (Redis)
      ↓
FastAPI Endpoint
      ↓
Redis Cache ──── hit ──→ Return instantly
      ↓ miss
PostgreSQL
      ↓
Populate Cache
      ↓
Record Click (PostgreSQL)
      ↓
Response
```

The redirect endpoint follows the **Cache-Aside** pattern — check Redis first, fall back to PostgreSQL on a miss, then populate the cache for subsequent requests.

---

## Project Structure

```
url-shortener/
├── docker-compose.yml        # All service definitions
├── Dockerfile                # App container build instructions
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (never commit)
├── .gitignore
└── app/
    ├── main.py               # FastAPI app entry point
    ├── config.py             # Settings management (Pydantic)
    ├── database.py           # PostgreSQL connection + session
    ├── cache.py              # Redis connection + cache operations
    ├── models.py             # SQLAlchemy ORM models
    ├── schemas.py            # Pydantic request/response schemas
    ├── routes/
    │   ├── urls.py           # POST, GET, DELETE endpoints
    │   └── analytics.py      # Analytics endpoint
    └── utils/
        ├── shortcode.py      # Short code generator
        ├── user_agent.py     # Browser/OS parser
        └── rate_limiter.py   # Redis-based rate limiting
```

---

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose installed
- Git

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/url-shortener.git
cd url-shortener
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Edit `.env` with your values (see [Environment Variables](#environment-variables)).

### 3. Start all services

```bash
docker compose up --build
```

This starts four services:
- **app** on `http://localhost:8000`
- **postgres** on `localhost:5432`
- **redis** on `localhost:6379`
- **pgadmin** on `http://localhost:5050`
- **redisinsight** on `http://localhost:5540`

### 4. Verify it's running

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

### 5. Open the interactive API docs

Visit `http://localhost:8000/docs` — FastAPI auto-generates a Swagger UI where you can test every endpoint directly in your browser.

---

## Environment Variables

Create a `.env` file in the project root:

```bash
# PostgreSQL
POSTGRES_USER=urluser
POSTGRES_PASSWORD=urlpassword
POSTGRES_DB=urlshortener
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# App
APP_SECRET_KEY=your-secret-key-change-this-in-production
BASE_URL=http://localhost:8000

# Cache
CACHE_TTL_SECONDS=3600
```

> **Note:** `POSTGRES_HOST=postgres` and `REDIS_HOST=redis` use the Docker service names, not `localhost`. Containers communicate with each other using service names as hostnames.

---

## API Reference

### Create a Short URL

```
POST /urls
```

**Request body:**

```json
{
  "original_url": "https://www.example.com/very/long/url",
  "custom_code": "mycode",
  "expires_at": "2025-12-31T23:59:59"
}
```

- `original_url` — required, must be a valid URL
- `custom_code` — optional, 3–10 characters, alphanumeric
- `expires_at` — optional, ISO 8601 datetime

**Response `201 Created`:**

```json
{
  "id": 1,
  "short_code": "mycode",
  "original_url": "https://www.example.com/very/long/url",
  "short_url": "http://localhost:8000/mycode",
  "created_at": "2024-01-01T00:00:00",
  "expires_at": "2025-12-31T23:59:59",
  "click_count": 0,
  "is_active": true
}
```

---

### Redirect to Original URL

```
GET /{short_code}
```

Redirects to the original URL with a `307 Temporary Redirect`.

**Possible responses:**
- `307` — success, redirecting
- `404` — short code not found or inactive
- `410` — short URL has expired

---

### Delete a Short URL

```
DELETE /urls/{short_code}
```

Soft-deletes the URL — sets `is_active = false` without removing the row or its click history.

**Response:** `204 No Content`

---

### Get Analytics

```
GET /urls/{short_code}/analytics
```

**Response `200 OK`:**

```json
{
  "url": {
    "short_code": "mycode",
    "original_url": "https://www.example.com",
    "click_count": 143,
    ...
  },
  "stats": {
    "total_clicks": 143,
    "clicks_today": 12,
    "clicks_by_day": [
      {"date": "2024-01-01", "count": 20},
      {"date": "2024-01-02", "count": 35}
    ],
    "top_referers": [
      {"referer": "https://twitter.com", "count": 45}
    ],
    "top_browsers": [
      {"browser": "Chrome", "count": 89}
    ],
    "top_countries": [
      {"country": "US", "count": 60}
    ]
  }
}
```

---

## Analytics

Click data is recorded on every redirect and includes:

| Field | Description |
|---|---|
| `clicked_at` | Timestamp of the click |
| `ip_address` | Visitor IP address |
| `referer` | Referring website (where they came from) |
| `user_agent` | Raw browser/OS string |
| `browser` | Parsed browser name (e.g. Chrome, Firefox) |
| `os` | Parsed operating system (e.g. Mac OS X, Windows) |
| `country` | Country code (populated when GeoIP is configured) |

> **Performance note:** Browser and OS are parsed from the raw user agent string at **write time** (when the click is recorded), not at query time. This keeps analytics queries fast — they're simple `GROUP BY` operations on pre-parsed string columns.

---

## Rate Limiting

Rate limits are applied per IP address using Redis counters with automatic expiry.

| Endpoint | Limit |
|---|---|
| `POST /urls` | 10 requests / minute |
| `GET /{short_code}` | 60 requests / minute |
| `GET /analytics` | 30 requests / minute |

When a limit is exceeded, the API returns `429 Too Many Requests` with headers indicating when to retry:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 45
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
```

---

## Database Schema

### `urls` table

| Column | Type | Description |
|---|---|---|
| `id` | integer | Primary key |
| `short_code` | varchar(10) | Unique short identifier |
| `original_url` | text | The destination URL |
| `created_at` | timestamptz | Creation timestamp |
| `expires_at` | timestamptz | Optional expiry (nullable) |
| `click_count` | integer | Denormalized click total |
| `is_active` | boolean | False = soft deleted |

### `clicks` table

| Column | Type | Description |
|---|---|---|
| `id` | integer | Primary key |
| `url_id` | integer | Foreign key → urls.id |
| `clicked_at` | timestamptz | Click timestamp |
| `ip_address` | varchar(45) | Visitor IP (IPv4 + IPv6) |
| `referer` | text | Referring URL |
| `user_agent` | text | Raw user agent string |
| `browser` | varchar(100) | Parsed browser name |
| `os` | varchar(100) | Parsed operating system |
| `country` | varchar(100) | Country (nullable) |

**Indexes:**
- `idx_short_code_active` — composite index on `(short_code, is_active)` for fast redirect lookups
- `idx_clicks_url_id` — index on `url_id` for fast analytics aggregation

---

## Caching Strategy

Redis caches URL data using the **Cache-Aside** pattern:

```
Key format:   url:{short_code}
Value:        JSON { id, original_url, expires_at }
TTL:          CACHE_TTL_SECONDS (default 1 hour)
```

**On redirect:** Check Redis → cache hit returns instantly without touching PostgreSQL.

**On cache miss:** Query PostgreSQL → store result in Redis → redirect.

**On delete:** Immediately invalidate the Redis key so deleted URLs can't be served from stale cache.

---

## Development Tools

All four tools are available after `docker compose up`:

| Tool | URL | Purpose |
|---|---|---|
| Swagger UI | `http://localhost:8000/docs` | Interactive API testing |
| pgAdmin | `http://localhost:5050` | PostgreSQL GUI |
| RedisInsight | `http://localhost:5540` | Redis GUI |
| Health check | `http://localhost:8000/health` | Verify app is running |

### pgAdmin login
- Email: `admin@admin.com`
- Password: `admin`
- Connect to host: `postgres`, port `5432`

### Useful commands

```bash
# View running containers
docker compose ps

# View app logs
docker compose logs app -f

# Access PostgreSQL CLI
docker compose exec postgres psql -U urluser -d urlshortener

# Access Redis CLI
docker compose exec redis redis-cli

# Stop all containers
docker compose down

# Stop and delete all data (fresh start)
docker compose down -v
```

---

---

## Concepts Covered

This project demonstrates the three core components found in almost every backend system:

- **REST API design** — proper HTTP methods, status codes, and resource naming
- **Relational database** — schema design, indexing, foreign keys, soft deletes
- **Caching** — Cache-Aside pattern, TTL management, cache invalidation
- **Rate limiting** — sliding window algorithm using Redis atomic counters
- **Data validation** — separating API schemas from database models
- **Containerization** — multi-service Docker Compose setup with health checks
