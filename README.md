# Testerfy

<img src="assets/logo.svg" alt="Testerfy Logo" width="128" />

Spotify controller with a lightweight web UI, plus automation for like/dislike flows.

## Quick Start (Docker)
```
cp env.example .env
```
Edit `.env` and set:
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_REDIRECT_URI`
- `SESSION_SECRET`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`

Build and run:
```
docker compose up -d --build postgres
docker compose --profile migrate run --rm migrate
docker compose up -d app
```
Open: `http://localhost:5247`

## Spotify Redirect URI
The app expects the callback path:
```
/api/auth/callback
```
Examples:
- Local: `http://localhost:5000/api/auth/callback`
- Tailscale: `https://your-tailnet.ts.net/api/auth/callback`
- Public: `https://your-domain.example.com/api/auth/callback`

Make sure the exact URI is registered in your Spotify Developer Dashboard.

## Tailscale (Private Access)
Set `TS_AUTHKEY` in `.env` and run:
```
docker compose --profile tailscale up -d tailscale app_tailscale
```

## Unraid + SWAG
See `DEPLOYMENT_UNRAID.md` for a full guide.
