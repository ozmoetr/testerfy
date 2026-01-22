# Unraid + SWAG Deployment (Docker)

This guide adds **deployment-only files** and does not change the existing app code.

## Prerequisites
- Unraid with Docker enabled
- SWAG container installed and working
- A domain/subdomain for public access, or a Tailscale MagicDNS name for private access
- A Spotify developer app with redirect URIs configured

## 1) Configure Spotify App
In the Spotify Developer Dashboard:
- Add redirect URIs for every hostname you will use, for example:
  - `https://testerfy.yourdomain.com/api/auth/callback`
  - `https://testerfy.tailnet123.ts.net/api/auth/callback`
- Ensure the exact URI matches your deployment (scheme + host + path).

## 2) Create Environment File
From the repo root:
```
cp env.example .env
```
Edit `.env` and set:
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_REDIRECT_URI`
- `SESSION_SECRET` (generate with `openssl rand -hex 32`)
- Postgres creds (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`)

**Important (Docker Compose warning fix):**
If your `SESSION_SECRET` contains `$`, Docker Compose will try to interpolate it and you’ll see warnings like:
`The "XYZ" variable is not set. Defaulting to a blank string.`

Fix: use a `$`-free secret (recommended) or escape `$` as `$$` in `.env`.

## 3) Build and Start with Docker Compose
From the repo root:

```
docker compose up -d --build postgres
docker compose --profile migrate run --rm migrate
docker compose up -d app
```

The app listens on container port `5000` and is mapped to host port `5247` (so it can run side-by-side with a test instance on `5000`).

## 4) Connect SWAG Reverse Proxy
### A) Add the app to SWAG's docker network
If your SWAG container uses a custom network (commonly named `swag`):
1. Create the network (if it does not exist):
   ```
   docker network create swag
   ```
2. Attach the app container to the SWAG network. In `compose.yml` add:
   ```
   networks:
     - swag
   ```
   And define at the bottom:
   ```
   networks:
     swag:
       external: true
   ```

### B) Add a new SWAG proxy config
Copy a sample proxy config in your SWAG appdata folder:
```
/config/nginx/proxy-confs/<yourapp>.subdomain.conf.sample
```
Rename it to:
```
/config/nginx/proxy-confs/testerfy.subdomain.conf
```
Set upstream to your app container name and port:
```
set $upstream_app app;
set $upstream_port 5000;
```
Reload or restart SWAG.

If you already host multiple sites, add one config per subdomain and ensure each `upstream_app` matches the container name for that service.

## 5) Private-Only Access (Optional)
If you want to avoid public exposure:
- Use Tailscale and set `SPOTIFY_REDIRECT_URI` to your MagicDNS hostname.
- Keep SWAG and the app reachable only via your Tailscale network or LAN.

### Enable the Tailscale sidecar
1) Create a reusable auth key in Tailscale and add it to `.env` as `TS_AUTHKEY`.
2) Start the Tailscale profile (this runs `tailscale`):
```
docker compose --profile tailscale up -d tailscale
```
3) Use the Tailscale MagicDNS hostname (from the Tailscale admin console) as your app URL.
Your app will be reachable at `http://testerfy:5000` on your tailnet, and the MagicDNS name externally.

## Troubleshooting
- If auth fails, verify `SPOTIFY_REDIRECT_URI` exactly matches the Spotify app settings.
- If the app cannot connect to Postgres, verify `POSTGRES_*` in `.env` and confirm the database container is healthy.

## Optional: Export actions for Unraid User Scripts (fail-safe cleanup)
If Spotify is slow/temporary rate-limited, skips can still work while playlist removals don’t always “stick” immediately. A safe way to harden this is to export your **like/dislike history** from Postgres and let an Unraid User Script do cleanup later (remove any liked/disliked tracks from your tester playlist, and ensure likes exist in target playlists).

### 1) Enable the exporter
In `.env`:
- `ENABLE_ACTION_EXPORTER=true`
- `EXPORT_INTERVAL_HOURS=3`
- `TESTER_PLAYLIST_ID=<your tester playlist id>` (e.g. Testercle)

Exports will be written to:
- `./exports/` in the repo folder (bind-mounted into the container as `/exports`)

### 2) Apply DB migrations + restart
```
docker compose --profile migrate run --rm migrate
docker compose up -d --build --force-recreate app
```

### 3) File format
For each user, files land under:
- `exports/user-<userId>/`

Each run writes:
- `song-actions_<from>-<to>_<timestamp>.jsonl` (newline-delimited JSON, one action per line)
- `summary_<from>-<to>_<timestamp>.json` (includes `TESTER_PLAYLIST_ID`, target playlists, and deduped lists)
- `latest.json` (points to the most recent export)

Your Unraid User Script can safely process each file once (or use the `from/to` range) to avoid reprocessing.

## Notes
- This deployment keeps your current app code unchanged.
- Do not commit `.env` to GitHub.
