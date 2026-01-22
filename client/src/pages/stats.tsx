import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ThumbsUp, ThumbsDown, ArrowLeft, Music } from "lucide-react";
import { Link } from "wouter";
import { ThemeToggle } from "@/components/theme-toggle";
import type { CurrentUserResponse } from "@shared/schema";

type SongActionHistory = {
  id: number;
  trackId: string;
  trackName: string;
  artistName: string;
  albumName: string | null;
  albumArt: string | null;
  action: string;
  sourcePlaylistName: string | null;
  createdAt: string;
};

type StatsSummary = {
  likes: number;
  dislikes: number;
};

export default function Stats() {
  const { data: user, isLoading: userLoading } = useQuery<CurrentUserResponse>({
    queryKey: ["/api/auth/me"],
  });

  const {
    data: stats,
    isLoading: statsLoading,
    isError: statsError,
    refetch: refetchStats,
  } = useQuery<StatsSummary>({
    queryKey: ["/api/stats/summary"],
    enabled: !!user,
    // Default queryClient has staleTime=Infinity; stats should always reflect recent actions.
    staleTime: 0,
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
    refetchInterval: 15000,
  });

  const {
    data: history,
    isLoading: historyLoading,
    isError: historyError,
    refetch: refetchHistory,
  } = useQuery<SongActionHistory[]>({
    queryKey: ["/api/stats/history"],
    enabled: !!user,
    staleTime: 0,
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
    refetchInterval: 15000,
  });

  if (userLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-background p-4">
        <p className="text-muted-foreground">Please log in to view your stats.</p>
        <Link href="/">
          <Button className="mt-4">Go Home</Button>
        </Link>
      </div>
    );
  }

  const total = (stats?.likes ?? 0) + (stats?.dislikes ?? 0);

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <header className="flex items-center justify-between p-4 border-b gap-4">
        <div className="flex items-center gap-2">
          <Link href="/">
            <Button variant="ghost" size="icon" data-testid="button-back">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <Music className="h-6 w-6 text-primary" />
          <span className="font-semibold text-lg">Stats</span>
        </div>
        <ThemeToggle />
      </header>

      <main className="flex-1 p-4 sm:p-8 space-y-6 max-w-2xl mx-auto w-full">
        {(statsLoading || historyLoading) && (
          <div className="text-sm text-muted-foreground">Refreshing…</div>
        )}
        {(statsError || historyError) && (
          <div className="flex items-center justify-between gap-3 text-sm text-muted-foreground">
            <span>Failed to load stats. This usually means the server/DB didn’t log actions or hasn’t been rebuilt.</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                refetchStats();
                refetchHistory();
              }}
            >
              Retry
            </Button>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <ThumbsUp className="h-4 w-4 text-primary" />
                Liked
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold" data-testid="text-likes-count">
                {stats?.likes ?? 0}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <ThumbsDown className="h-4 w-4 text-destructive" />
                Disliked
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold" data-testid="text-dislikes-count">
                {stats?.dislikes ?? 0}
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Total Songs Processed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold" data-testid="text-total-count">
              {total}
            </div>
            {total > 0 && (
              <p className="text-sm text-muted-foreground mt-2">
                {((stats?.likes ?? 0) / total * 100).toFixed(0)}% like rate
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {!history || history.length === 0 ? (
              <div className="p-6 text-center text-muted-foreground">
                No activity yet. Start rating songs!
              </div>
            ) : (
              <div className="divide-y max-h-96 overflow-y-auto">
                {history.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center gap-3 p-4"
                    data-testid={`history-item-${item.id}`}
                  >
                    {item.albumArt ? (
                      <img
                        src={item.albumArt}
                        alt={item.albumName ?? "Album"}
                        className="w-12 h-12 rounded object-cover shrink-0"
                      />
                    ) : (
                      <div className="w-12 h-12 rounded bg-muted flex items-center justify-center shrink-0">
                        <Music className="h-6 w-6 text-muted-foreground" />
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{item.trackName}</p>
                      <p className="text-sm text-muted-foreground truncate">
                        {item.artistName}
                      </p>
                      {item.sourcePlaylistName && (
                        <p className="text-xs text-muted-foreground/70 truncate">
                          from {item.sourcePlaylistName}
                        </p>
                      )}
                    </div>
                    <div className="shrink-0">
                      {item.action === 'like' ? (
                        <ThumbsUp className="h-5 w-5 text-primary" />
                      ) : (
                        <ThumbsDown className="h-5 w-5 text-destructive" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
