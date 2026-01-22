import { drizzle } from "drizzle-orm/node-postgres";
import pg from "pg";
import * as schema from "@shared/schema";

const { Pool } = pg;

if (!process.env.DATABASE_URL) {
  throw new Error(
    "DATABASE_URL must be set. Did you forget to provision a database?",
  );
}

export const pool = new Pool({ connectionString: process.env.DATABASE_URL });
export const db = drizzle(pool, { schema });

// Idempotent schema guardrails to avoid "migrations missed" breaking core functionality.
// This keeps the app reliable in environments where `drizzle-kit push` isn't always run.
export async function ensureDbSchema(): Promise<void> {
  // NOTE: These are intentionally minimal and additive (no drops).
  // They are safe to run repeatedly.
  await pool.query(`
    CREATE TABLE IF NOT EXISTS users (
      id SERIAL PRIMARY KEY,
      spotify_id TEXT NOT NULL UNIQUE,
      display_name TEXT,
      access_token TEXT,
      refresh_token TEXT,
      token_expiry TIMESTAMP
    );
  `);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS target_playlists (
      id SERIAL PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES users(id),
      playlist_id TEXT NOT NULL,
      playlist_name TEXT NOT NULL
    );
  `);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS approved_source_playlists (
      id SERIAL PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES users(id),
      playlist_id TEXT NOT NULL,
      playlist_name TEXT NOT NULL
    );
  `);
  await pool.query(`
    CREATE UNIQUE INDEX IF NOT EXISTS approved_source_user_playlist_unique
    ON approved_source_playlists (user_id, playlist_id);
  `);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS song_actions (
      id SERIAL PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES users(id),
      track_id TEXT NOT NULL,
      track_name TEXT NOT NULL,
      artist_name TEXT NOT NULL,
      album_name TEXT,
      album_art TEXT,
      action TEXT NOT NULL,
      source_playlist_id TEXT,
      source_playlist_name TEXT,
      guard_blocked BOOLEAN NOT NULL DEFAULT FALSE,
      created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
  `);

  // Additive columns for newer versions.
  await pool.query(`ALTER TABLE song_actions ADD COLUMN IF NOT EXISTS track_uri TEXT;`);
  await pool.query(`ALTER TABLE song_actions ADD COLUMN IF NOT EXISTS guard_blocked BOOLEAN NOT NULL DEFAULT FALSE;`);
  await pool.query(`ALTER TABLE song_actions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();`);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS testerfy_sessions (
      sid VARCHAR(255) PRIMARY KEY,
      sess JSONB NOT NULL,
      expire TIMESTAMP NOT NULL
    );
  `);
  await pool.query(`CREATE INDEX IF NOT EXISTS testerfy_sessions_expire_idx ON testerfy_sessions (expire);`);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS export_cursors (
      id SERIAL PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES users(id) UNIQUE,
      last_song_action_id INTEGER NOT NULL DEFAULT 0,
      updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
  `);
}
