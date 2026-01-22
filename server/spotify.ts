import { storage } from "./storage";

const SPOTIFY_API_URL = "https://api.spotify.com/v1";
const SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token";

const SPOTIFY_CLIENT_ID = process.env.SPOTIFY_CLIENT_ID;
const SPOTIFY_CLIENT_SECRET = process.env.SPOTIFY_CLIENT_SECRET;

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function parseRetryAfterSeconds(value: string | null): number | null {
  if (!value) return null;
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0) return null;
  return n;
}

async function refreshTokenIfNeeded(userId: number): Promise<string | null> {
  const user = await storage.getUserById(userId);
  if (!user || !user.refreshToken) return null;

  if (user.tokenExpiry && new Date(user.tokenExpiry) > new Date()) {
    return user.accessToken;
  }

  if (!SPOTIFY_CLIENT_ID || !SPOTIFY_CLIENT_SECRET) return null;

  const response = await fetch(SPOTIFY_TOKEN_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Authorization: `Basic ${Buffer.from(`${SPOTIFY_CLIENT_ID}:${SPOTIFY_CLIENT_SECRET}`).toString("base64")}`,
    },
    body: new URLSearchParams({
      grant_type: "refresh_token",
      refresh_token: user.refreshToken,
    }),
  });

  if (!response.ok) return null;

  const data = await response.json();
  const tokenExpiry = new Date(Date.now() + data.expires_in * 1000);

  await storage.updateUser(userId, {
    accessToken: data.access_token,
    tokenExpiry,
    ...(data.refresh_token && { refreshToken: data.refresh_token }),
  });

  return data.access_token;
}

type CacheEntry<T> = { value: T; expiresAtMs: number };

const playlistsCache = new Map<number, CacheEntry<any>>();
const playlistsInFlight = new Map<number, Promise<any>>();

const playlistNameCache = new Map<string, CacheEntry<string | null>>();
const playlistNameInFlight = new Map<string, Promise<string | null>>();

export async function spotifyFetch(userId: number, endpoint: string, options: RequestInit = {}) {
  const accessToken = await refreshTokenIfNeeded(userId);
  if (!accessToken) throw new Error("No valid access token");

  const maxRetries = 3;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const response = await fetch(`${SPOTIFY_API_URL}${endpoint}`, {
      ...options,
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (response.status === 204) return null;

    // Respect Spotify rate-limits by waiting Retry-After and retrying a few times.
    if (response.status === 429 && attempt < maxRetries) {
      const retryAfter = parseRetryAfterSeconds(response.headers.get("retry-after")) ?? 1;
      const waitMs = Math.min(30_000, retryAfter * 1000 + Math.floor(Math.random() * 250));
      await sleep(waitMs);
      continue;
    }

    if (!response.ok) {
      const retryAfter = parseRetryAfterSeconds(response.headers.get("retry-after"));
      const body = await response.text();
      if (response.status === 429) {
        throw new Error(`Spotify API error: 429 - Too many requests (retry-after=${retryAfter ?? "?"}s) - ${body}`);
      }
      throw new Error(`Spotify API error: ${response.status} - ${body}`);
    }

    return response.json();
  }
}

export async function getUserPlaylistsCached(userId: number) {
  const now = Date.now();
  const cached = playlistsCache.get(userId);
  if (cached && cached.expiresAtMs > now) return cached.value;

  const inFlight = playlistsInFlight.get(userId);
  if (inFlight) return await inFlight;

  const p = (async () => {
    const data = await spotifyFetch(userId, "/me/playlists?limit=50");
    const items = data?.items ?? [];
    playlistsCache.set(userId, { value: items, expiresAtMs: now + 5 * 60 * 1000 });
    return items;
  })().finally(() => {
    playlistsInFlight.delete(userId);
  });

  playlistsInFlight.set(userId, p);
  return await p;
}

export async function getPlaylistNameCached(userId: number, playlistId: string) {
  const key = `${userId}:${playlistId}`;
  const now = Date.now();
  const cached = playlistNameCache.get(key);
  if (cached && cached.expiresAtMs > now) return cached.value;

  const inFlight = playlistNameInFlight.get(key);
  if (inFlight) return await inFlight;

  const p = (async () => {
    const playlist = await spotifyFetch(userId, `/playlists/${playlistId}?fields=name`);
    const name = (playlist as any)?.name ?? null;
    playlistNameCache.set(key, { value: name, expiresAtMs: now + 10 * 60 * 1000 });
    return name;
  })().finally(() => {
    playlistNameInFlight.delete(key);
  });

  playlistNameInFlight.set(key, p);
  return await p;
}

