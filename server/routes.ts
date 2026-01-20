import type { Express, Request, Response, NextFunction } from "express";
import type { Server } from "http";
import session from "express-session";
import { z } from "zod";
import { storage } from "./storage";
import { api, buildUrl } from "@shared/routes";

const SPOTIFY_CLIENT_ID = process.env.SPOTIFY_CLIENT_ID;
const SPOTIFY_CLIENT_SECRET = process.env.SPOTIFY_CLIENT_SECRET;

// Build the redirect URI from the current domain
function getRedirectUri(): string {
  // If explicitly set, use that
  if (process.env.SPOTIFY_REDIRECT_URI) {
    return process.env.SPOTIFY_REDIRECT_URI;
  }
  // Use the Replit dev domain if available
  if (process.env.REPLIT_DEV_DOMAIN) {
    return `https://${process.env.REPLIT_DEV_DOMAIN}/api/auth/callback`;
  }
  // Fallback for local development
  return "http://localhost:5000/api/auth/callback";
}

const SPOTIFY_REDIRECT_URI = getRedirectUri();

const SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize";
const SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token";
const SPOTIFY_API_URL = "https://api.spotify.com/v1";

const SCOPES = [
  "user-read-playback-state",
  "user-modify-playback-state",
  "user-read-currently-playing",
  "playlist-read-private",
  "playlist-read-collaborative",
  "playlist-modify-public",
  "playlist-modify-private",
].join(" ");

declare module "express-session" {
  interface SessionData {
    userId?: number;
  }
}

function requireAuth(req: Request, res: Response, next: NextFunction) {
  if (!req.session.userId) {
    return res.status(401).json({ message: "Not authenticated" });
  }
  next();
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

async function spotifyFetch(userId: number, endpoint: string, options: RequestInit = {}) {
  const accessToken = await refreshTokenIfNeeded(userId);
  if (!accessToken) throw new Error("No valid access token");

  const response = await fetch(`${SPOTIFY_API_URL}${endpoint}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (response.status === 204) return null;
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Spotify API error: ${response.status} - ${error}`);
  }

  return response.json();
}

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {

  app.use(
    session({
      secret: process.env.SESSION_SECRET || "testerfy-session-secret",
      resave: false,
      saveUninitialized: false,
      proxy: true,
      cookie: {
        // "auto" respects req.secure when behind a trusted proxy.
        secure: "auto",
        httpOnly: true,
        sameSite: "lax",
        maxAge: 7 * 24 * 60 * 60 * 1000,
      },
    })
  );

  app.get(api.auth.login.path, (req, res) => {
    const clientId = process.env.SPOTIFY_CLIENT_ID;
    const clientSecret = process.env.SPOTIFY_CLIENT_SECRET;

    if (!clientId || !clientSecret) {
      console.error("Missing credentials:", { clientId: !!clientId, clientSecret: !!clientSecret });
      return res.status(500).json({ 
        message: "Spotify credentials not configured. Please add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET as Secrets.",
        details: { hasClientId: !!clientId, hasClientSecret: !!clientSecret }
      });
    }

    const params = new URLSearchParams({
      client_id: clientId,
      response_type: "code",
      redirect_uri: SPOTIFY_REDIRECT_URI,
      scope: SCOPES,
      show_dialog: "true",
    });

    res.redirect(`${SPOTIFY_AUTH_URL}?${params}`);
  });

  app.get(api.auth.callback.path, async (req, res) => {
    const { code, error } = req.query;
    const clientId = process.env.SPOTIFY_CLIENT_ID;
    const clientSecret = process.env.SPOTIFY_CLIENT_SECRET;

    if (error || !code) {
      return res.redirect("/?error=auth_failed");
    }

    if (!clientId || !clientSecret) {
      return res.redirect("/?error=no_credentials");
    }

    try {
      const tokenResponse = await fetch(SPOTIFY_TOKEN_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          Authorization: `Basic ${Buffer.from(`${clientId}:${clientSecret}`).toString("base64")}`,
        },
        body: new URLSearchParams({
          grant_type: "authorization_code",
          code: code as string,
          redirect_uri: SPOTIFY_REDIRECT_URI,
        }),
      });

      if (!tokenResponse.ok) {
        return res.redirect("/?error=token_failed");
      }

      const tokens = await tokenResponse.json();

      const profileResponse = await fetch(`${SPOTIFY_API_URL}/me`, {
        headers: { Authorization: `Bearer ${tokens.access_token}` },
      });

      if (!profileResponse.ok) {
        return res.redirect("/?error=profile_failed");
      }

      const profile = await profileResponse.json();
      const tokenExpiry = new Date(Date.now() + tokens.expires_in * 1000);

      let user = await storage.getUserBySpotifyId(profile.id);

      if (user) {
        user = await storage.updateUser(user.id, {
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          tokenExpiry,
          displayName: profile.display_name,
        });
      } else {
        user = await storage.createUser({
          spotifyId: profile.id,
          displayName: profile.display_name,
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          tokenExpiry,
        });
      }


  req.session.userId = user.id;
  req.session.save((err) => {
    if (err) {
      console.error("Session save error:", err);
      return res.redirect("/?error=session_error");
    }
    return res.redirect("/");
  });
    } catch (err) {
      console.error("Auth callback error:", err);
      res.redirect("/?error=auth_error");
    }
  });

  app.post(api.auth.logout.path, (req, res) => {
    req.session.destroy((err) => {
      res.json({ success: !err });
    });
  });

  app.get(api.auth.me.path, async (req, res) => {
    if (!req.session.userId) {
      return res.json(null);
    }

    const user = await storage.getUserById(req.session.userId);
    if (!user) {
      return res.json(null);
    }

    res.json({
      id: user.id,
      spotifyId: user.spotifyId,
      displayName: user.displayName,
    });
  });

  app.get(api.playlists.list.path, requireAuth, async (req, res) => {
    try {
      const data = await spotifyFetch(req.session.userId!, "/me/playlists?limit=50");
      res.json(data.items);
    } catch (err) {
      console.error("Playlists fetch error:", err);
      res.status(500).json({ message: "Failed to fetch playlists" });
    }
  });

  app.get(api.targetPlaylists.list.path, requireAuth, async (req, res) => {
    const playlists = await storage.getTargetPlaylists(req.session.userId!);
    res.json(playlists);
  });

  app.post(api.targetPlaylists.add.path, requireAuth, async (req, res) => {
    try {
      const input = api.targetPlaylists.add.input.parse(req.body);
      const playlist = await storage.addTargetPlaylist({
        userId: req.session.userId!,
        playlistId: input.playlistId,
        playlistName: input.playlistName,
      });
      res.status(201).json(playlist);
    } catch (err) {
      if (err instanceof z.ZodError) {
        return res.status(400).json({ message: err.errors[0].message });
      }
      throw err;
    }
  });

  app.delete(buildUrl(api.targetPlaylists.remove.path, { id: ":id" }), requireAuth, async (req, res) => {
    await storage.removeTargetPlaylist(Number(req.params.id), req.session.userId!);
    res.status(204).send();
  });

  app.get(api.player.current.path, requireAuth, async (req, res) => {
    try {
      const data = await spotifyFetch(req.session.userId!, "/me/player/currently-playing");
      
      if (data?.context?.uri && data.context.type === "playlist") {
        const playlistId = data.context.uri.split(":").pop();
        try {
          const playlist = await spotifyFetch(req.session.userId!, `/playlists/${playlistId}?fields=name`);
          if (playlist?.name) {
            data.context.name = playlist.name;
          }
        } catch (err) {
          // Playlist name fetch failed, continue without it
        }
      }
      
      res.json(data);
    } catch (err) {
      console.error("Player state error:", err);
      res.json(null);
    }
  });

  app.post(api.player.like.path, requireAuth, async (req, res) => {
    try {
      // `/me/player` tends to include richer context than `/me/player/currently-playing` on some devices.
      // We still fall back to `currently-playing` in case `/me/player` returns no item.
      const playerState = await spotifyFetch(req.session.userId!, "/me/player");
      const playbackState = playerState?.item
        ? playerState
        : await spotifyFetch(req.session.userId!, "/me/player/currently-playing");
      
      if (!playbackState?.item) {
        return res.status(400).json({ message: "No track currently playing" });
      }

      const trackUri = playbackState.item.uri;
      const trackId = playbackState.item.id;
      const contextUri = playbackState.context?.uri;
      const contextType = playbackState.context?.type;

      const targetPlaylists = await storage.getTargetPlaylists(req.session.userId!);

      let addedToTargets = 0;
      const addErrors: string[] = [];
      let removedFromSource = false;
      let removalError: string | undefined;

      for (const target of targetPlaylists) {
        try {
          await spotifyFetch(req.session.userId!, `/playlists/${target.playlistId}/tracks`, {
            method: "POST",
            body: JSON.stringify({ uris: [trackUri] }),
          });
          addedToTargets += 1;
        } catch (err) {
          console.error(`Failed to add to playlist ${target.playlistId}:`, err);
          addErrors.push(err instanceof Error ? err.message : String(err));
        }
      }

      if (contextUri && (contextType === "playlist" || contextUri.includes(":playlist:") || contextUri.includes("playlist"))) {
        const playlistId = contextUri.split(":").pop();
        try {
          await spotifyFetch(req.session.userId!, `/playlists/${playlistId}/tracks`, {
            method: "DELETE",
            body: JSON.stringify({ tracks: [{ uri: trackUri }] }),
          });
          removedFromSource = true;
        } catch (err) {
          console.error("Failed to remove from current playlist:", err);
          removalError = err instanceof Error ? err.message : String(err);
        }
      }

      try {
        await spotifyFetch(req.session.userId!, "/me/player/next", { method: "POST" });
      } catch (err) {
        console.error("Failed to skip:", err);
      }

      // Log the action
      let sourcePlaylistName: string | undefined;
      if (contextUri && contextUri.includes("playlist")) {
        const playlistId = contextUri.split(":").pop();
        try {
          const playlist = await spotifyFetch(req.session.userId!, `/playlists/${playlistId}?fields=name`);
          sourcePlaylistName = playlist?.name;
        } catch {}
      }
      
      await storage.addSongAction({
        userId: req.session.userId!,
        trackId: playbackState.item.id,
        trackName: playbackState.item.name,
        artistName: playbackState.item.artists.map((a: { name: string }) => a.name).join(", "),
        albumName: playbackState.item.album?.name,
        albumArt: playbackState.item.album?.images?.[0]?.url,
        action: 'like',
        sourcePlaylistId: contextUri?.split(":").pop(),
        sourcePlaylistName,
      });

      res.json({
        success: true,
        addedToTargets,
        targetPlaylistsCount: targetPlaylists.length,
        addErrors: addErrors.length ? addErrors.slice(0, 3) : undefined,
        removedFromSource,
        removalError,
        sourceContext: contextType ? { type: contextType, uri: contextUri ?? null } : null,
      });
    } catch (err) {
      console.error("Like action error:", err);
      res.status(500).json({ message: "Failed to process like action" });
    }
  });

  app.post(api.player.dislike.path, requireAuth, async (req, res) => {
    try {
      // `/me/player` tends to include richer context than `/me/player/currently-playing` on some devices.
      // We still fall back to `currently-playing` in case `/me/player` returns no item.
      const playerState = await spotifyFetch(req.session.userId!, "/me/player");
      const playbackState = playerState?.item
        ? playerState
        : await spotifyFetch(req.session.userId!, "/me/player/currently-playing");
      
      if (!playbackState?.item) {
        return res.status(400).json({ message: "No track currently playing" });
      }

      const trackUri = playbackState.item.uri;
      const contextUri = playbackState.context?.uri;
      const trackId = playbackState.item.id;
      const contextType = playbackState.context?.type;

      let removedFromSource = false;
      let removalTarget: "playlist" | "library" | null = null;
      let removalError: string | undefined;

      // Remove from the current *source* when possible.
      // - playlist: remove track from playlist
      // - collection (Liked Songs): remove track from library
      if (contextUri && (contextType === "playlist" || contextUri.includes(":playlist:") || contextUri.includes("playlist"))) {
        const playlistId = contextUri.split(":").pop();
        if (playlistId) {
          try {
            await spotifyFetch(req.session.userId!, `/playlists/${playlistId}/tracks`, {
              method: "DELETE",
              body: JSON.stringify({ tracks: [{ uri: trackUri }] }),
            });
            removedFromSource = true;
            removalTarget = "playlist";
          } catch (err) {
            removalError = err instanceof Error ? err.message : String(err);
            console.error("Failed to remove from current playlist:", err);
          }
        }
      } else if (contextUri && (contextType === "collection" || contextUri.includes(":collection"))) {
        // "Liked Songs" behaves like a playlist in the Spotify UI, but is a library collection in the API.
        if (trackId) {
          try {
            await spotifyFetch(req.session.userId!, `/me/tracks?ids=${encodeURIComponent(trackId)}`, {
              method: "DELETE",
            });
            removedFromSource = true;
            removalTarget = "library";
          } catch (err) {
            removalError = err instanceof Error ? err.message : String(err);
            console.error("Failed to remove from library:", err);
          }
        }
      }

      try {
        await spotifyFetch(req.session.userId!, "/me/player/next", { method: "POST" });
      } catch (err) {
        console.error("Failed to skip:", err);
      }

      // Log the action
      let sourcePlaylistName: string | undefined;
      if (contextUri && contextUri.includes("playlist")) {
        const playlistId = contextUri.split(":").pop();
        try {
          const playlist = await spotifyFetch(req.session.userId!, `/playlists/${playlistId}?fields=name`);
          sourcePlaylistName = playlist?.name;
        } catch {}
      }
      
      await storage.addSongAction({
        userId: req.session.userId!,
        trackId: playbackState.item.id,
        trackName: playbackState.item.name,
        artistName: playbackState.item.artists.map((a: { name: string }) => a.name).join(", "),
        albumName: playbackState.item.album?.name,
        albumArt: playbackState.item.album?.images?.[0]?.url,
        action: 'dislike',
        sourcePlaylistId: contextUri?.split(":").pop(),
        sourcePlaylistName,
      });

      // Keep backwards-compat `success`, but include useful debug fields for troubleshooting.
      res.json({
        success: true,
        removedFromSource,
        removalTarget,
        removalError,
        sourceContext: contextType ? { type: contextType, uri: contextUri ?? null } : null,
      });
    } catch (err) {
      console.error("Dislike action error:", err);
      res.status(500).json({ message: "Failed to process dislike action" });
    }
  });

  app.post(api.player.skip.path, requireAuth, async (req, res) => {
    try {
      await spotifyFetch(req.session.userId!, "/me/player/next", { method: "POST" });
      res.json({ success: true });
    } catch (err) {
      console.error("Skip error:", err);
      res.status(500).json({ message: "Failed to skip" });
    }
  });

  app.post(api.player.play.path, requireAuth, async (req, res) => {
    try {
      await spotifyFetch(req.session.userId!, "/me/player/play", { method: "PUT" });
      res.json({ success: true });
    } catch (err) {
      console.error("Play error:", err);
      res.status(500).json({ message: "Failed to play" });
    }
  });

  app.post(api.player.pause.path, requireAuth, async (req, res) => {
    try {
      await spotifyFetch(req.session.userId!, "/me/player/pause", { method: "PUT" });
      res.json({ success: true });
    } catch (err) {
      console.error("Pause error:", err);
      res.status(500).json({ message: "Failed to pause" });
    }
  });

  app.post(api.player.previous.path, requireAuth, async (req, res) => {
    try {
      await spotifyFetch(req.session.userId!, "/me/player/previous", { method: "POST" });
      res.json({ success: true });
    } catch (err) {
      console.error("Previous error:", err);
      res.status(500).json({ message: "Failed to go to previous" });
    }
  });

  app.get(api.player.getShuffleState.path, requireAuth, async (req, res) => {
    try {
      const data = await spotifyFetch(req.session.userId!, "/me/player");
      res.json({ shuffle_state: data?.shuffle_state ?? false });
    } catch (err) {
      console.error("Get shuffle state error:", err);
      res.json({ shuffle_state: false });
    }
  });

  app.post(api.player.shuffle.path, requireAuth, async (req, res) => {
    try {
      const { state } = req.body;
      await spotifyFetch(req.session.userId!, `/me/player/shuffle?state=${state}`, { method: "PUT" });
      res.json({ success: true, shuffle_state: state });
    } catch (err) {
      console.error("Shuffle error:", err);
      res.status(500).json({ message: "Failed to toggle shuffle" });
    }
  });

  app.post(api.player.seek.path, requireAuth, async (req, res) => {
    try {
      const { position_ms } = req.body;
      await spotifyFetch(req.session.userId!, `/me/player/seek?position_ms=${position_ms}`, { method: "PUT" });
      res.json({ success: true });
    } catch (err) {
      console.error("Seek error:", err);
      res.status(500).json({ message: "Failed to seek" });
    }
  });

  // Stats routes
  app.get(api.stats.summary.path, requireAuth, async (req, res) => {
    try {
      const stats = await storage.getSongActionStats(req.session.userId!);
      res.json(stats);
    } catch (err) {
      console.error("Stats summary error:", err);
      res.status(500).json({ message: "Failed to get stats" });
    }
  });

  app.get(api.stats.history.path, requireAuth, async (req, res) => {
    try {
      const history = await storage.getSongActions(req.session.userId!, 100);
      res.json(history.map(h => ({
        ...h,
        createdAt: h.createdAt.toISOString(),
      })));
    } catch (err) {
      console.error("Stats history error:", err);
      res.status(500).json({ message: "Failed to get history" });
    }
  });

  return httpServer;
}
