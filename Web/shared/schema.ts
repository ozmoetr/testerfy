import { pgTable, text, varchar, serial, integer, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  spotifyId: text("spotify_id").notNull().unique(),
  displayName: text("display_name"),
  accessToken: text("access_token"),
  refreshToken: text("refresh_token"),
  tokenExpiry: timestamp("token_expiry"),
});

export const targetPlaylists = pgTable("target_playlists", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").references(() => users.id).notNull(),
  playlistId: text("playlist_id").notNull(),
  playlistName: text("playlist_name").notNull(),
});

export const songActions = pgTable("song_actions", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").references(() => users.id).notNull(),
  trackId: text("track_id").notNull(),
  trackName: text("track_name").notNull(),
  artistName: text("artist_name").notNull(),
  albumName: text("album_name"),
  albumArt: text("album_art"),
  action: text("action").notNull(), // 'like' or 'dislike'
  sourcePlaylistId: text("source_playlist_id"),
  sourcePlaylistName: text("source_playlist_name"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const insertUserSchema = createInsertSchema(users).omit({ id: true });
export const insertTargetPlaylistSchema = createInsertSchema(targetPlaylists).omit({ id: true });
export const insertSongActionSchema = createInsertSchema(songActions).omit({ id: true, createdAt: true });

export type User = typeof users.$inferSelect;
export type InsertUser = z.infer<typeof insertUserSchema>;
export type TargetPlaylist = typeof targetPlaylists.$inferSelect;
export type InsertTargetPlaylist = z.infer<typeof insertTargetPlaylistSchema>;
export type SongAction = typeof songActions.$inferSelect;
export type InsertSongAction = z.infer<typeof insertSongActionSchema>;

export type SpotifyPlaylist = {
  id: string;
  name: string;
  images: { url: string }[];
  tracks: { total: number };
};

export type SpotifyTrack = {
  id: string;
  name: string;
  artists: { name: string }[];
  album: {
    name: string;
    images: { url: string }[];
  };
  duration_ms: number;
};

export type PlaybackState = {
  is_playing: boolean;
  item: SpotifyTrack | null;
  progress_ms: number;
  context: {
    uri: string;
    type: string;
    name?: string;
  } | null;
};

export type CurrentUserResponse = {
  id: number;
  spotifyId: string;
  displayName: string | null;
} | null;
