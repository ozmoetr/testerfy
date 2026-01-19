import { z } from 'zod';

export const errorSchemas = {
  validation: z.object({
    message: z.string(),
    field: z.string().optional(),
  }),
  notFound: z.object({
    message: z.string(),
  }),
  unauthorized: z.object({
    message: z.string(),
  }),
  internal: z.object({
    message: z.string(),
  }),
};

export const api = {
  auth: {
    login: {
      method: 'GET' as const,
      path: '/api/auth/login',
      responses: {
        302: z.void(),
      },
    },
    callback: {
      method: 'GET' as const,
      path: '/api/auth/callback',
      responses: {
        302: z.void(),
      },
    },
    logout: {
      method: 'POST' as const,
      path: '/api/auth/logout',
      responses: {
        200: z.object({ success: z.boolean() }),
      },
    },
    me: {
      method: 'GET' as const,
      path: '/api/auth/me',
      responses: {
        200: z.object({
          id: z.number(),
          spotifyId: z.string(),
          displayName: z.string().nullable(),
        }).nullable(),
      },
    },
  },
  playlists: {
    list: {
      method: 'GET' as const,
      path: '/api/playlists',
      responses: {
        200: z.array(z.object({
          id: z.string(),
          name: z.string(),
          images: z.array(z.object({ url: z.string() })),
          tracks: z.object({ total: z.number() }),
        })),
        401: errorSchemas.unauthorized,
      },
    },
  },
  targetPlaylists: {
    list: {
      method: 'GET' as const,
      path: '/api/target-playlists',
      responses: {
        200: z.array(z.object({
          id: z.number(),
          userId: z.number(),
          playlistId: z.string(),
          playlistName: z.string(),
        })),
        401: errorSchemas.unauthorized,
      },
    },
    add: {
      method: 'POST' as const,
      path: '/api/target-playlists',
      input: z.object({
        playlistId: z.string(),
        playlistName: z.string(),
      }),
      responses: {
        201: z.object({
          id: z.number(),
          userId: z.number(),
          playlistId: z.string(),
          playlistName: z.string(),
        }),
        401: errorSchemas.unauthorized,
      },
    },
    remove: {
      method: 'DELETE' as const,
      path: '/api/target-playlists/:id',
      responses: {
        204: z.void(),
        401: errorSchemas.unauthorized,
        404: errorSchemas.notFound,
      },
    },
  },
  player: {
    current: {
      method: 'GET' as const,
      path: '/api/player/current',
      responses: {
        200: z.object({
          is_playing: z.boolean(),
          item: z.object({
            id: z.string(),
            name: z.string(),
            artists: z.array(z.object({ name: z.string() })),
            album: z.object({
              name: z.string(),
              images: z.array(z.object({ url: z.string() })),
            }),
            duration_ms: z.number(),
          }).nullable(),
          progress_ms: z.number(),
          context: z.object({
            uri: z.string(),
            type: z.string(),
          }).nullable(),
        }).nullable(),
        401: errorSchemas.unauthorized,
      },
    },
    like: {
      method: 'POST' as const,
      path: '/api/player/like',
      responses: {
        200: z.object({ success: z.boolean() }),
        401: errorSchemas.unauthorized,
      },
    },
    dislike: {
      method: 'POST' as const,
      path: '/api/player/dislike',
      responses: {
        200: z.object({
          success: z.boolean(),
          removedFromSource: z.boolean().optional(),
          removalTarget: z.enum(["playlist", "library"]).nullable().optional(),
          removalError: z.string().optional(),
          sourceContext: z.object({
            type: z.string(),
            uri: z.string().nullable(),
          }).nullable().optional(),
        }),
        401: errorSchemas.unauthorized,
      },
    },
    skip: {
      method: 'POST' as const,
      path: '/api/player/skip',
      responses: {
        200: z.object({ success: z.boolean() }),
        401: errorSchemas.unauthorized,
      },
    },
    play: {
      method: 'POST' as const,
      path: '/api/player/play',
      responses: {
        200: z.object({ success: z.boolean() }),
        401: errorSchemas.unauthorized,
      },
    },
    pause: {
      method: 'POST' as const,
      path: '/api/player/pause',
      responses: {
        200: z.object({ success: z.boolean() }),
        401: errorSchemas.unauthorized,
      },
    },
    previous: {
      method: 'POST' as const,
      path: '/api/player/previous',
      responses: {
        200: z.object({ success: z.boolean() }),
        401: errorSchemas.unauthorized,
      },
    },
    shuffle: {
      method: 'POST' as const,
      path: '/api/player/shuffle',
      input: z.object({ state: z.boolean() }),
      responses: {
        200: z.object({ success: z.boolean(), shuffle_state: z.boolean() }),
        401: errorSchemas.unauthorized,
      },
    },
    getShuffleState: {
      method: 'GET' as const,
      path: '/api/player/shuffle',
      responses: {
        200: z.object({ shuffle_state: z.boolean() }),
        401: errorSchemas.unauthorized,
      },
    },
    seek: {
      method: 'POST' as const,
      path: '/api/player/seek',
      input: z.object({ position_ms: z.number() }),
      responses: {
        200: z.object({ success: z.boolean() }),
        401: errorSchemas.unauthorized,
      },
    },
  },
  stats: {
    summary: {
      method: 'GET' as const,
      path: '/api/stats/summary',
      responses: {
        200: z.object({
          likes: z.number(),
          dislikes: z.number(),
        }),
        401: errorSchemas.unauthorized,
      },
    },
    history: {
      method: 'GET' as const,
      path: '/api/stats/history',
      responses: {
        200: z.array(z.object({
          id: z.number(),
          trackId: z.string(),
          trackName: z.string(),
          artistName: z.string(),
          albumName: z.string().nullable(),
          albumArt: z.string().nullable(),
          action: z.string(),
          sourcePlaylistName: z.string().nullable(),
          createdAt: z.string(),
        })),
        401: errorSchemas.unauthorized,
      },
    },
  },
};

export function buildUrl(path: string, params?: Record<string, string | number>): string {
  let url = path;
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (url.includes(`:${key}`)) {
        url = url.replace(`:${key}`, String(value));
      }
    });
  }
  return url;
}

export type TargetPlaylistInput = z.infer<typeof api.targetPlaylists.add.input>;
export type TargetPlaylistResponse = z.infer<typeof api.targetPlaylists.add.responses[201]>;
export type PlaylistResponse = z.infer<typeof api.playlists.list.responses[200]>[number];
export type PlaybackStateResponse = z.infer<typeof api.player.current.responses[200]>;
