import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Plus, Trash2, Music, ListMusic, Shield } from "lucide-react";
import { Link, useLocation } from "wouter";
import { ThemeToggle } from "@/components/theme-toggle";
import type { CurrentUserResponse, SpotifyPlaylist, TargetPlaylist, ApprovedSourcePlaylist } from "@shared/schema";

export default function Settings() {
  const [, setLocation] = useLocation();

  const { data: user, isLoading: userLoading } = useQuery<CurrentUserResponse>({
    queryKey: ["/api/auth/me"],
  });

  const {
    data: playlists,
    isLoading: playlistsLoading,
    isError: playlistsError,
  } = useQuery<SpotifyPlaylist[]>({
    queryKey: ["/api/playlists"],
    enabled: !!user,
  });

  const {
    data: approvedSourcePlaylists,
    isLoading: approvedLoading,
    isError: approvedError,
  } = useQuery<ApprovedSourcePlaylist[]>({
    queryKey: ["/api/approved-source-playlists"],
    enabled: !!user,
  });

  const {
    data: targetPlaylists,
    isLoading: targetsLoading,
    isError: targetsError,
  } = useQuery<TargetPlaylist[]>({
    queryKey: ["/api/target-playlists"],
    enabled: !!user,
  });

  const addMutation = useMutation({
    mutationFn: (playlist: SpotifyPlaylist) =>
      apiRequest("POST", "/api/target-playlists", {
        playlistId: playlist.id,
        playlistName: playlist.name,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/target-playlists"] });
    },
  });

  const removeMutation = useMutation({
    mutationFn: (id: number) =>
      apiRequest("DELETE", `/api/target-playlists/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/target-playlists"] });
    },
  });

  const addApprovedMutation = useMutation({
    mutationFn: (playlist: SpotifyPlaylist) =>
      apiRequest("POST", "/api/approved-source-playlists", {
        playlistId: playlist.id,
        playlistName: playlist.name,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/approved-source-playlists"] });
    },
  });

  const removeApprovedMutation = useMutation({
    mutationFn: (id: number) =>
      apiRequest("DELETE", `/api/approved-source-playlists/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/approved-source-playlists"] });
    },
  });

  if (userLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (!user) {
    setLocation("/");
    return null;
  }

  const targetPlaylistIds = new Set(targetPlaylists?.map(t => t.playlistId) || []);
  const availablePlaylists = playlists?.filter(p => !targetPlaylistIds.has(p.id)) || [];

  const approvedPlaylistIds = new Set(approvedSourcePlaylists?.map(p => p.playlistId) || []);
  const availableApprovedPlaylists = playlists?.filter(p => !approvedPlaylistIds.has(p.id)) || [];

  const renderPlaylistRow = (
    playlist: SpotifyPlaylist,
    onAdd: () => void,
    disabled: boolean,
    testIdPrefix: string
  ) => (
    <div
      key={playlist.id}
      className="flex items-center gap-3 p-3 bg-muted/30 rounded-md hover-elevate"
      data-testid={`${testIdPrefix}-playlist-${playlist.id}`}
    >
      {playlist.images[0]?.url ? (
        <img
          src={playlist.images[0].url}
          alt={playlist.name}
          className="w-10 h-10 rounded object-cover"
        />
      ) : (
        <div className="w-10 h-10 rounded bg-muted flex items-center justify-center">
          <Music className="h-5 w-5 text-muted-foreground" />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">{playlist.name}</div>
        <div className="text-sm text-muted-foreground">{playlist.tracks.total} tracks</div>
      </div>
      <Button
        variant="ghost"
        size="icon"
        onClick={onAdd}
        disabled={disabled}
        data-testid={`${testIdPrefix}-button-add-${playlist.id}`}
        aria-label={`Add ${playlist.name}`}
      >
        <Plus className="h-4 w-4" />
      </Button>
    </div>
  );

  return (
    <div className="min-h-screen bg-background">
      <header className="flex items-center justify-between p-4 border-b gap-4">
        <div className="flex items-center gap-2">
          <Link href="/">
            <Button variant="ghost" size="icon" data-testid="button-back">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <span className="font-semibold text-lg">Settings</span>
        </div>
        <ThemeToggle />
      </header>

      <main className="max-w-2xl mx-auto p-4 sm:p-8 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Approved Source Playlists (Safeguard)
            </CardTitle>
            <CardDescription>
              Optional. If set, likes/dislikes will only add/remove tracks when you are playing from one of these playlists.
              Skipping still works anywhere.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <div className="text-sm font-medium">Currently approved</div>
              {approvedLoading ? (
                <div className="text-muted-foreground">Loading...</div>
              ) : approvedError ? (
                <div className="text-muted-foreground text-sm py-2">
                  Failed to load approved playlists.
                </div>
              ) : (approvedSourcePlaylists?.length ?? 0) === 0 ? (
                <div className="text-muted-foreground text-sm py-2">
                  None. Safeguard is currently disabled.
                </div>
              ) : (
                approvedSourcePlaylists?.map((p) => (
                  <div
                    key={p.id}
                    className="flex items-center justify-between p-3 bg-muted/50 rounded-md"
                    data-testid={`approved-source-playlist-${p.id}`}
                  >
                    <span className="font-medium truncate flex-1">{p.playlistName}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => removeApprovedMutation.mutate(p.id)}
                      disabled={removeApprovedMutation.isPending}
                      data-testid={`button-approved-remove-${p.id}`}
                      aria-label={`Remove ${p.playlistName}`}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                ))
              )}
            </div>

            <div className="pt-2 border-t space-y-2">
              <div className="text-sm font-medium">Add approved playlists</div>
              {playlistsLoading ? (
                <div className="text-muted-foreground">Loading your playlists...</div>
              ) : playlistsError ? (
                <div className="text-muted-foreground text-sm py-2">
                  Failed to load your Spotify playlists.
                </div>
              ) : availableApprovedPlaylists.length === 0 ? (
                <div className="text-muted-foreground text-sm py-2">
                  {playlists?.length === 0
                    ? "No playlists found in your Spotify account."
                    : "All your playlists are already approved."}
                </div>
              ) : (
                <div className="max-h-72 overflow-y-auto space-y-2">
                  {availableApprovedPlaylists.map((playlist) =>
                    renderPlaylistRow(
                      playlist,
                      () => addApprovedMutation.mutate(playlist),
                      addApprovedMutation.isPending,
                      "approve"
                    )
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ListMusic className="h-5 w-5" />
              Target Playlists
            </CardTitle>
            <CardDescription>
              When you like a song, it will be saved to these playlists
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <div className="text-sm font-medium">Current targets</div>
              {targetsLoading ? (
                <div className="text-muted-foreground">Loading...</div>
              ) : targetsError ? (
                <div className="text-muted-foreground text-sm py-2">
                  Failed to load target playlists.
                </div>
              ) : targetPlaylists?.length === 0 ? (
                <div className="text-muted-foreground text-sm py-2">
                  None selected yet.
                </div>
              ) : (
                targetPlaylists?.map(target => (
                  <div
                    key={target.id}
                    className="flex items-center justify-between p-3 bg-muted/50 rounded-md"
                    data-testid={`target-playlist-${target.id}`}
                  >
                    <span className="font-medium truncate flex-1">{target.playlistName}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => removeMutation.mutate(target.id)}
                      disabled={removeMutation.isPending}
                      data-testid={`button-remove-${target.id}`}
                      aria-label={`Remove ${target.playlistName}`}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                ))
              )}
            </div>

            <div className="pt-2 border-t space-y-2">
              <div className="text-sm font-medium">Add target playlists</div>
              {playlistsLoading ? (
                <div className="text-muted-foreground">Loading your playlists...</div>
              ) : playlistsError ? (
                <div className="text-muted-foreground text-sm py-2">
                  Failed to load your Spotify playlists.
                </div>
              ) : availablePlaylists.length === 0 ? (
                <div className="text-muted-foreground text-sm py-2">
                  {playlists?.length === 0
                    ? "No playlists found in your Spotify account."
                    : "All your playlists are already added as targets."}
                </div>
              ) : (
                <div className="max-h-72 overflow-y-auto space-y-2">
                  {availablePlaylists.map((playlist) =>
                    renderPlaylistRow(
                      playlist,
                      () => addMutation.mutate(playlist),
                      addMutation.isPending,
                      "targets"
                    )
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
