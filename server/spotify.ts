import { storage } from "./storage";
import { Buffer } from "buffer";

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

async function refreshToken(userId: number): Promise<string | null> {
  const user = await storage.getUserById(userId);
  if (!user || !user.refreshToken) return null;

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

async function getAccessToken(userId: number): Promise<string | null> {
  const user = await storage.getUserById(userId);
  if (!user || !user.refreshToken) return null;

  if (user.tokenExpiry && new Date(user.tokenExpiry) > new Date() && user.accessToken) {
    return user.accessToken;
  }

  return await refreshToken(userId);
}

type CacheEntry<T> = { value: T; expiresAtMs: number };

const playlistsCache = new Map<number, CacheEntry<any>>();
const playlistsInFlight = new Map<number, Promise<any>>();

const playlistNameCache = new Map<string, CacheEntry<string | null>>();
const playlistNameInFlight = new Map<string, Promise<string | null>>();

export async function spotifyFetch(userId: number, endpoint: string, options: RequestInit = {}) {
  // For user-triggered actions we can wait a bit on rate limits, but we should not hang forever.
  // Polling endpoints should call `spotifyFetchFast` instead.
  const maxRetries = 2;
  const maxTotalWaitMs = 8000;
  return await spotifyFetchInternal(userId, endpoint, options, { maxRetries, maxTotalWaitMs });
}

async function spotifyFetchInternal(
  userId: number,
  endpoint: string,
  options: RequestInit,
  policy: { maxRetries: number; maxTotalWaitMs: number }
) {
  let accessToken = await getAccessToken(userId);
  if (!accessToken) throw new Error("No valid access token");

  let totalWaitMs = 0;
  let didForceRefresh = false;

  for (let attempt = 0; attempt <= policy.maxRetries; attempt++) {
    const response = await fetch(`${SPOTIFY_API_URL}${endpoint}`, {
      ...options,
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (response.status === 204) return null;

    // Sometimes tokens get invalidated early; refresh once and retry.
    if (response.status === 401 && !didForceRefresh) {
      const refreshed = await refreshToken(userId);
      if (refreshed) {
        accessToken = refreshed;
        didForceRefresh = true;
        continue;
      }
    }

    // Respect Spotify rate-limits by waiting Retry-After and retrying a few times,
    // but never block longer than maxTotalWaitMs.
    if (response.status === 429 && attempt < policy.maxRetries && policy.maxTotalWaitMs > 0) {
      const retryAfter = parseRetryAfterSeconds(response.headers.get("retry-after")) ?? 1;
      const proposedWaitMs = retryAfter * 1000 + Math.floor(Math.random() * 250);
      const remainingWaitMs = Math.max(0, policy.maxTotalWaitMs - totalWaitMs);
      const waitMs = Math.min(5000, proposedWaitMs, remainingWaitMs);
      if (waitMs <= 0) break;
      await sleep(waitMs);
      totalWaitMs += waitMs;
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

  throw new Error("Spotify API error: request aborted due to rate limiting");
}

export async function spotifyFetchFast(userId: number, endpoint: string, options: RequestInit = {}) {
  // For polling/UX reads: do not wait on 429. If we’re rate-limited, fail fast and let callers use stale cache.
  return await spotifyFetchInternal(userId, endpoint, options, { maxRetries: 0, maxTotalWaitMs: 0 });
}

export async function getUserPlaylistsCached(userId: number) {
  const now = Date.now();
  const cached = playlistsCache.get(userId);
  if (cached && cached.expiresAtMs > now) return cached.value;

  const inFlight = playlistsInFlight.get(userId);
  if (inFlight) return await inFlight;

  const p = (async () => {
    try {
      const data = await spotifyFetchFast(userId, "/me/playlists?limit=50");
      const items = data?.items ?? [];
      playlistsCache.set(userId, { value: items, expiresAtMs: now + 5 * 60 * 1000 });
      return items;
    } catch (err) {
      // If Spotify is rate-limiting, serve stale cache (even if expired) to keep UI responsive.
      if (cached) return cached.value;
      throw err;
    }
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
    try {
      const playlist = await spotifyFetchFast(userId, `/playlists/${playlistId}?fields=name`);
      const name = (playlist as any)?.name ?? null;
      playlistNameCache.set(key, { value: name, expiresAtMs: now + 10 * 60 * 1000 });
      return name;
    } catch (err) {
      // If we’re rate-limited (or Spotify transiently fails), don’t block the main response.
      if (cached) return cached.value;
      return null;
    }
  })().finally(() => {
    playlistNameInFlight.delete(key);
  });

  playlistNameInFlight.set(key, p);
  return await p;
}

