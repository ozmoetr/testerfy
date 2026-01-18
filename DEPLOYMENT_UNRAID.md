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

## 3) Build and Start with Docker Compose
From the repo root:
```
docker compose up -d --build postgres
docker compose --profile migrate run --rm migrate
docker compose up -d app
```

The app listens on container port `5000`. You can map it to a host port via `APP_PORT` in `.env`.

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
set $upstream_app testerfy_app;
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
2) Start the Tailscale profile (this runs `tailscale` + `app_tailscale`):
```
docker compose --profile tailscale up -d tailscale app_tailscale
```
3) Use the Tailscale MagicDNS hostname (from the Tailscale admin console) as your app URL.
Your app will be reachable at `http://testerfy:5000` on your tailnet, and the MagicDNS name externally.

## Troubleshooting
- If auth fails, verify `SPOTIFY_REDIRECT_URI` exactly matches the Spotify app settings.
- If the app cannot connect to Postgres, verify `POSTGRES_*` in `.env` and confirm the database container is healthy.

## Notes
- This deployment keeps your current app code unchanged.
- Do not commit `.env` to GitHub.
