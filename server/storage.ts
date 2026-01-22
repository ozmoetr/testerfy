import { db } from "./db";
import {
  users,
  targetPlaylists,
  approvedSourcePlaylists,
  songActions,
  type User,
  type InsertUser,
  type TargetPlaylist,
  type InsertTargetPlaylist,
  type ApprovedSourcePlaylist,
  type InsertApprovedSourcePlaylist,
  type SongAction,
  type InsertSongAction,
} from "@shared/schema";
import { eq, and, desc, sql } from "drizzle-orm";

export interface IStorage {
  getUserBySpotifyId(spotifyId: string): Promise<User | undefined>;
  getUserById(id: number): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  updateUser(id: number, updates: Partial<InsertUser>): Promise<User>;
  getTargetPlaylists(userId: number): Promise<TargetPlaylist[]>;
  addTargetPlaylist(playlist: InsertTargetPlaylist): Promise<TargetPlaylist>;
  removeTargetPlaylist(id: number, userId: number): Promise<void>;
  getApprovedSourcePlaylists(userId: number): Promise<ApprovedSourcePlaylist[]>;
  addApprovedSourcePlaylist(playlist: InsertApprovedSourcePlaylist): Promise<ApprovedSourcePlaylist>;
  removeApprovedSourcePlaylist(id: number, userId: number): Promise<void>;
  addSongAction(action: InsertSongAction): Promise<SongAction>;
  getSongActions(userId: number, limit?: number): Promise<SongAction[]>;
  getSongActionStats(userId: number): Promise<{ likes: number; dislikes: number }>;
}

export class DatabaseStorage implements IStorage {
  async getUserBySpotifyId(spotifyId: string): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.spotifyId, spotifyId));
    return user;
  }

  async getUserById(id: number): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.id, id));
    return user;
  }

  async createUser(user: InsertUser): Promise<User> {
    const [created] = await db.insert(users).values(user).returning();
    return created;
  }

  async updateUser(id: number, updates: Partial<InsertUser>): Promise<User> {
    const [updated] = await db.update(users).set(updates).where(eq(users.id, id)).returning();
    return updated;
  }

  async getTargetPlaylists(userId: number): Promise<TargetPlaylist[]> {
    return await db.select().from(targetPlaylists).where(eq(targetPlaylists.userId, userId));
  }

  async addTargetPlaylist(playlist: InsertTargetPlaylist): Promise<TargetPlaylist> {
    const [created] = await db.insert(targetPlaylists).values(playlist).returning();
    return created;
  }

  async removeTargetPlaylist(id: number, userId: number): Promise<void> {
    await db.delete(targetPlaylists).where(
      and(eq(targetPlaylists.id, id), eq(targetPlaylists.userId, userId))
    );
  }

  async getApprovedSourcePlaylists(userId: number): Promise<ApprovedSourcePlaylist[]> {
    return await db.select().from(approvedSourcePlaylists).where(eq(approvedSourcePlaylists.userId, userId));
  }

  async addApprovedSourcePlaylist(playlist: InsertApprovedSourcePlaylist): Promise<ApprovedSourcePlaylist> {
    const [created] = await db.insert(approvedSourcePlaylists).values(playlist).returning();
    return created;
  }

  async removeApprovedSourcePlaylist(id: number, userId: number): Promise<void> {
    await db.delete(approvedSourcePlaylists).where(
      and(eq(approvedSourcePlaylists.id, id), eq(approvedSourcePlaylists.userId, userId))
    );
  }

  async addSongAction(action: InsertSongAction): Promise<SongAction> {
    const [created] = await db.insert(songActions).values(action).returning();
    return created;
  }

  async getSongActions(userId: number, limit: number = 100): Promise<SongAction[]> {
    return await db.select().from(songActions)
      .where(eq(songActions.userId, userId))
      .orderBy(desc(songActions.createdAt))
      .limit(limit);
  }

  async getSongActionStats(userId: number): Promise<{ likes: number; dislikes: number }> {
    const result = await db.select({
      action: songActions.action,
      count: sql<number>`count(*)::int`,
    })
      .from(songActions)
      .where(eq(songActions.userId, userId))
      .groupBy(songActions.action);
    
    const likes = result.find(r => r.action === 'like')?.count ?? 0;
    const dislikes = result.find(r => r.action === 'dislike')?.count ?? 0;
    return { likes, dislikes };
  }
}

export const storage = new DatabaseStorage();
