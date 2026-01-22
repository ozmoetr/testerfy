import { promises as fs } from "fs";
import path from "path";
import { storage } from "./storage";
import type { SongAction, TargetPlaylist } from "@shared/schema";

function log(message: string) {
  const formattedTime = new Date().toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });
  console.log(`${formattedTime} [exporter] ${message}`);
}

type ExportSummary = {
  generatedAt: string;
  userId: number;
  fromSongActionIdExclusive: number;
  toSongActionIdInclusive: number;
  exportedCount: number;
  testerPlaylistId: string | null;
  targetPlaylists: Array<{ playlistId: string; playlistName: string }>;
  removeFromTester: Array<{ trackId: string; trackUri?: string | null; lastAction: "like" | "dislike" }>;
  ensureInTargets: Array<{ trackId: string; trackUri?: string | null }>;
};

function toSafeTimestamp(ts: Date) {
  return ts.toISOString().replace(/[:.]/g, "-");
}

function parseHours(value: string | undefined, fallback: number) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return fallback;
  return n;
}

function parseIntSafe(value: string | undefined, fallback: number) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return fallback;
  return Math.floor(n);
}

function dedupeLatestByTrack(actions: SongAction[]) {
  const byTrack = new Map<string, SongAction>();
  for (const a of actions) {
    const existing = byTrack.get(a.trackId);
    if (!existing || a.id > existing.id) byTrack.set(a.trackId, a);
  }
  return Array.from(byTrack.values()).sort((a, b) => a.id - b.id);
}

async function ensureDir(dir: string) {
  await fs.mkdir(dir, { recursive: true });
}

async function writeJsonAtomic(filePath: string, data: unknown) {
  const tmp = `${filePath}.tmp`;
  await fs.writeFile(tmp, JSON.stringify(data, null, 2) + "\n", "utf8");
  await fs.rename(tmp, filePath);
}

async function exportForUser(userId: number, exportDir: string, maxActions: number, testerPlaylistId: string | null) {
  const lastCursor = await storage.getExportCursor(userId);
  const actions = await storage.getSongActionsSinceId(userId, lastCursor, maxActions);
  if (actions.length === 0) return;

  const toId = actions[actions.length - 1]!.id;
  const generatedAt = new Date();
  const stamp = toSafeTimestamp(generatedAt);

  const userDir = path.join(exportDir, `user-${userId}`);
  await ensureDir(userDir);

  const actionsPath = path.join(userDir, `song-actions_${lastCursor + 1}-${toId}_${stamp}.jsonl`);
  const summaryPath = path.join(userDir, `summary_${lastCursor + 1}-${toId}_${stamp}.json`);
  const latestPath = path.join(userDir, "latest.json");

  // Write JSONL (one record per line) so Unraid scripts can stream process.
  const lines = actions.map((a) =>
    JSON.stringify({
      id: a.id,
      createdAt: a.createdAt,
      action: a.action,
      guardBlocked: a.guardBlocked,
      trackId: a.trackId,
      trackUri: a.trackUri ?? null,
      trackName: a.trackName,
      artistName: a.artistName,
      albumName: a.albumName ?? null,
      sourcePlaylistId: a.sourcePlaylistId ?? null,
      sourcePlaylistName: a.sourcePlaylistName ?? null,
    }),
  );
  await fs.writeFile(actionsPath, lines.join("\n") + "\n", "utf8");

  const targetPlaylists: TargetPlaylist[] = await storage.getTargetPlaylists(userId);

  // “Remove from tester” should include both likes and dislikes, even if guard blocked at the time.
  // We export only the latest action per track for dedupe.
  const latestByTrack = dedupeLatestByTrack(actions);

  const removeFromTester = latestByTrack.map((a) => ({
    trackId: a.trackId,
    trackUri: a.trackUri ?? null,
    lastAction: (a.action === "like" ? "like" : "dislike") as "like" | "dislike",
  }));

  // “Ensure in targets” only needs likes (latest action per track is like).
  const ensureInTargets = latestByTrack
    .filter((a) => a.action === "like")
    .map((a) => ({ trackId: a.trackId, trackUri: a.trackUri ?? null }));

  const summary: ExportSummary = {
    generatedAt: generatedAt.toISOString(),
    userId,
    fromSongActionIdExclusive: lastCursor,
    toSongActionIdInclusive: toId,
    exportedCount: actions.length,
    testerPlaylistId,
    targetPlaylists: targetPlaylists.map((t) => ({ playlistId: t.playlistId, playlistName: t.playlistName })),
    removeFromTester,
    ensureInTargets,
  };

  await writeJsonAtomic(summaryPath, summary);
  await writeJsonAtomic(latestPath, { ...summary, actionsFile: path.basename(actionsPath), summaryFile: path.basename(summaryPath) });

  await storage.setExportCursor(userId, toId);
}

export function startActionExporter() {
  const enabled = (process.env.ENABLE_ACTION_EXPORTER ?? "").toLowerCase() === "true";
  if (!enabled) return;

  const exportDir = process.env.EXPORT_DIR || "/exports";
  const intervalHours = parseHours(process.env.EXPORT_INTERVAL_HOURS, 3);
  const maxActions = parseIntSafe(process.env.EXPORT_MAX_ACTIONS, 5000);
  const testerPlaylistId = process.env.TESTER_PLAYLIST_ID || null;

  // Fire once shortly after boot, then on interval.
  const run = async () => {
    try {
      await ensureDir(exportDir);
      const users = await storage.getAllUsers();
      for (const u of users) {
        await exportForUser(u.id, exportDir, maxActions, testerPlaylistId);
      }
    } catch (err) {
      console.error("Action exporter error:", err);
    }
  };

  setTimeout(run, 15_000);
  setInterval(run, Math.max(10 * 60 * 1000, intervalHours * 60 * 60 * 1000));
  log(`action exporter enabled (dir=${exportDir}, intervalHours=${intervalHours}, maxActions=${maxActions})`);
}

