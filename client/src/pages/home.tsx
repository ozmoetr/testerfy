import { useQuery, useMutation } from "@tanstack/react-query";
import { useEffect, useCallback, useState, useRef } from "react";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ThumbsUp, ThumbsDown, SkipForward, SkipBack, Play, Pause, Settings, Music, LogOut, ListMusic, Shuffle, BarChart2, Plus, X } from "lucide-react";
import { Link } from "wouter";
import { ThemeToggle } from "@/components/theme-toggle";
import { useSwipeable } from "react-swipeable";
import { useAlbumColor } from "@/hooks/use-album-color";
import { useToast } from "@/hooks/use-toast";
import type { CurrentUserResponse, PlaybackState } from "@shared/schema";

export default function Home() {
  const { toast } = useToast();
  const [isTabVisible, setIsTabVisible] = useState(true);
  const { data: user, isLoading: userLoading } = useQuery<CurrentUserResponse>({
    queryKey: ["/api/auth/me"],
  });

  const { data: playbackState, refetch: refetchPlayback } = useQuery<PlaybackState | null>({
    queryKey: ["/api/player/current"],
    enabled: !!user,
    refetchInterval: (query) => {
      if (!isTabVisible) return false;
      // Faster while playing, slower while paused.
      const data = query.state.data;
      if (data?.is_playing) return 3000;
      return 7000;
    },
    refetchIntervalInBackground: false,
  });

  const { data: targetPlaylists } = useQuery({
    queryKey: ["/api/target-playlists"],
    enabled: !!user,
  });

  const { data: shuffleData, refetch: refetchShuffle } = useQuery<{ shuffle_state: boolean }>({
    queryKey: ["/api/player/shuffle"],
    enabled: !!user,
  });

  const shuffleMutation = useMutation({
    mutationFn: (state: boolean) => apiRequest("POST", "/api/player/shuffle", { state }),
    onSuccess: () => {
      refetchShuffle();
    },
  });

  const likeMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", "/api/player/like");
      return await res.json().catch(() => null);
    },
    onSuccess: (data: any) => {
      if (data?.guardBlocked) {
        toast({
          variant: "warning",
          title: "Safeguard active",
          description: data.guardMessage || "Playlist changes were blocked because the current playlist is not approved.",
        });
      }
      queryClient.invalidateQueries({ queryKey: ["/api/stats/summary"] });
      queryClient.invalidateQueries({ queryKey: ["/api/stats/history"] });
      setTimeout(() => refetchPlayback(), 450);
    },
  });

  const dislikeMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", "/api/player/dislike");
      return await res.json().catch(() => null);
    },
    onSuccess: (data: any) => {
      if (data?.guardBlocked) {
        toast({
          variant: "warning",
          title: "Safeguard active",
          description: data.guardMessage || "Playlist changes were blocked because the current playlist is not approved.",
        });
      }
      queryClient.invalidateQueries({ queryKey: ["/api/stats/summary"] });
      queryClient.invalidateQueries({ queryKey: ["/api/stats/history"] });
      setTimeout(() => refetchPlayback(), 450);
    },
  });

  const skipMutation = useMutation({
    mutationFn: () => apiRequest("POST", "/api/player/skip"),
    onSuccess: () => {
      setTimeout(() => refetchPlayback(), 400);
    },
  });

  const playMutation = useMutation({
    mutationFn: () => apiRequest("POST", "/api/player/play"),
    onSuccess: () => {
      setTimeout(() => refetchPlayback(), 500);
    },
  });

  const pauseMutation = useMutation({
    mutationFn: () => apiRequest("POST", "/api/player/pause"),
    onSuccess: () => {
      setTimeout(() => refetchPlayback(), 500);
    },
  });

  const previousMutation = useMutation({
    mutationFn: () => apiRequest("POST", "/api/player/previous"),
    onSuccess: () => {
      setTimeout(() => refetchPlayback(), 400);
    },
  });

  const seekMutation = useMutation({
    mutationFn: (position_ms: number) => apiRequest("POST", "/api/player/seek", { position_ms }),
    onSuccess: () => {
      setTimeout(() => refetchPlayback(), 300);
    },
  });

  const logoutMutation = useMutation({
    mutationFn: () => apiRequest("POST", "/api/auth/logout"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/auth/me"] });
    },
  });

  const [isMobile, setIsMobile] = useState(false);
  const [swipeDirection, setSwipeDirection] = useState<'left' | 'right' | null>(null);
  const [swipeProgress, setSwipeProgress] = useState(0); // 0 to 1, tracks how far user has swiped
  const [showSwipeNudge, setShowSwipeNudge] = useState(false);
  const nudgeShownRef = useRef(false);

  // Get album art color for dynamic theming
  const albumArtUrl = playbackState?.item?.album.images[0]?.url;
  const { color: albumColor } = useAlbumColor(albumArtUrl);

  useEffect(() => {
    const updateVisibility = () => setIsTabVisible(!document.hidden);
    updateVisibility();
    document.addEventListener("visibilitychange", updateVisibility);
    return () => document.removeEventListener("visibilitychange", updateVisibility);
  }, []);

  // Only Home should disable scrolling on small mobile screens (for swipe UX).
  // Settings/Stats must remain scrollable.
  useEffect(() => {
    const html = document.documentElement;
    const body = document.body;
    const shouldLock = window.matchMedia("(max-width: 640px)").matches && isMobile;
    if (shouldLock) {
      html.classList.add("testerfy-scroll-lock");
      body.classList.add("testerfy-scroll-lock");
    }
    return () => {
      html.classList.remove("testerfy-scroll-lock");
      body.classList.remove("testerfy-scroll-lock");
    };
  }, [isMobile]);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile('ontouchstart' in window || navigator.maxTouchPoints > 0);
    };
    checkMobile();
  }, []);

  // Show swipe nudge once when first track loads on mobile
  useEffect(() => {
    if (isMobile && playbackState?.item && !nudgeShownRef.current) {
      nudgeShownRef.current = true;
      setTimeout(() => {
        setShowSwipeNudge(true);
        setTimeout(() => setShowSwipeNudge(false), 1500);
      }, 500);
    }
  }, [isMobile, playbackState?.item]);

  const handleLike = useCallback(() => {
    if (!likeMutation.isPending && !dislikeMutation.isPending) {
      likeMutation.mutate();
    }
  }, [likeMutation, dislikeMutation]);

  const handleDislike = useCallback(() => {
    if (!likeMutation.isPending && !dislikeMutation.isPending) {
      dislikeMutation.mutate();
    }
  }, [likeMutation, dislikeMutation]);

  // Keyboard shortcuts (desktop only)
  useEffect(() => {
    if (isMobile || !user) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+Shift+Enter = Like
      if (e.ctrlKey && e.shiftKey && e.key === 'Enter') {
        e.preventDefault();
        handleLike();
      }
      // Ctrl+Shift+Delete or Ctrl+Shift+Backspace = Dislike
      if (e.ctrlKey && e.shiftKey && (e.key === 'Delete' || e.key === 'Backspace')) {
        e.preventDefault();
        handleDislike();
      }
      // Spacebar = Play/Pause (when not in input)
      if (e.key === ' ' && e.target === document.body) {
        e.preventDefault();
        if (playbackState?.is_playing) {
          pauseMutation.mutate();
        } else {
          playMutation.mutate();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isMobile, user, handleLike, handleDislike, playbackState?.is_playing, playMutation, pauseMutation]);

  // Swipe handlers (mobile only)
  const swipeHandlers = useSwipeable({
    onSwiping: (eventData) => {
      if (isMobile) {
        const { deltaX } = eventData;
        // Require more distance (150px for full intensity) for more obvious feedback
        const progress = Math.min(Math.abs(deltaX) / 150, 1);
        setSwipeProgress(progress);
        if (deltaX < -10) {
          setSwipeDirection('left');
        } else if (deltaX > 10) {
          setSwipeDirection('right');
        } else {
          setSwipeDirection(null);
        }
      }
    },
    onSwipedLeft: () => {
      if (isMobile) {
        handleDislike();
        setTimeout(() => {
          setSwipeDirection(null);
          setSwipeProgress(0);
        }, 300);
      }
    },
    onSwipedRight: () => {
      if (isMobile) {
        handleLike();
        setTimeout(() => {
          setSwipeDirection(null);
          setSwipeProgress(0);
        }, 300);
      }
    },
    onTouchEndOrOnMouseUp: () => {
      // Reset if swipe wasn't completed
      setTimeout(() => {
        setSwipeProgress(0);
        setSwipeDirection(null);
      }, 100);
    },
    trackMouse: false,
    trackTouch: true,
    delta: 80, // Require more initial movement to trigger swipe
    preventScrollOnSwipe: true,
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
        <div className="absolute top-4 right-4">
          <ThemeToggle />
        </div>
        <div className="text-center space-y-6 max-w-md">
          <div className="flex items-center justify-center gap-3">
            <Music className="h-12 w-12 text-primary" />
            <h1 className="text-4xl font-bold">Testerfy</h1>
          </div>
          <p className="text-muted-foreground text-lg">
            Your Spotify companion for testing new music. Like or dislike songs to quickly curate your playlists.
          </p>
          <Button
            size="lg"
            className="gap-2"
            onClick={() => window.location.href = "/api/auth/login"}
            data-testid="button-login"
          >
            <Music className="h-5 w-5" />
            Connect with Spotify
          </Button>
          <p className="text-sm text-muted-foreground">
            Make sure you have Spotify open and playing music from a playlist.
          </p>
        </div>
      </div>
    );
  }

  const track = playbackState?.item;
  const albumArt = track?.album.images[0]?.url;
  const artistNames = track?.artists.map(a => a.name).join(", ");
  const isPlaying = playbackState?.is_playing ?? false;
  const isActionPending = likeMutation.isPending || dislikeMutation.isPending || skipMutation.isPending;
  const isPlaybackPending = playMutation.isPending || pauseMutation.isPending || previousMutation.isPending || skipMutation.isPending;

  const formatTime = (ms: number) => {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const progressMs = playbackState?.progress_ms ?? 0;
  const durationMs = track?.duration_ms ?? 0;
  const progressPercent = durationMs > 0 ? Math.min(100, Math.max(0, (progressMs / durationMs) * 100)) : 0;

  // Generate background gradient from album color with smooth transition
  const backgroundStyle = {
    background: albumColor 
      ? `linear-gradient(to bottom, ${albumColor} 0%, hsl(var(--background)) 50%)`
      : undefined,
    transition: 'background 0.5s ease-in-out'
  };

  return (
    <div className="h-[100dvh] flex flex-col bg-background overflow-hidden" style={backgroundStyle}>
      <header className="flex items-center justify-between p-2 sm:p-4 border-b gap-2 sm:gap-4 shrink-0">
        <div className="flex items-center gap-1 sm:gap-2">
          <Music className="h-5 w-5 sm:h-6 sm:w-6 text-primary" />
          <span className="font-semibold text-base sm:text-lg">Testerfy</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground hidden sm:block">
            {user.displayName}
          </span>
          <Link href="/stats">
            <Button variant="ghost" size="icon" data-testid="button-stats">
              <BarChart2 className="h-5 w-5" />
            </Button>
          </Link>
          <Link href="/settings">
            <Button variant="ghost" size="icon" data-testid="button-settings">
              <Settings className="h-5 w-5" />
            </Button>
          </Link>
          <ThemeToggle />
          <Button
            variant="ghost"
            size="icon"
            onClick={() => logoutMutation.mutate()}
            data-testid="button-logout"
          >
            <LogOut className="h-5 w-5" />
          </Button>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center p-2 sm:p-8 overflow-hidden relative">
        {/* Swipe feedback overlays - mobile only - more pronounced */}
        {isMobile && swipeDirection === 'right' && swipeProgress > 0 && (
          <div 
            className="fixed inset-y-0 left-0 pointer-events-none z-40 flex items-center justify-start pl-6"
            style={{ 
              width: `${Math.max(80, swipeProgress * 160)}px`,
              background: `linear-gradient(to right, rgba(34, 197, 94, ${Math.min(swipeProgress * 0.85, 0.85)}), transparent)`,
            }}
          >
            <div 
              className="flex items-center gap-1 text-white font-bold drop-shadow-lg"
              style={{ opacity: Math.min(swipeProgress * 1.5, 1), transform: `scale(${1 + swipeProgress * 0.3})` }}
            >
              <Plus className="h-10 w-10" strokeWidth={3} />
            </div>
          </div>
        )}
        {isMobile && swipeDirection === 'left' && swipeProgress > 0 && (
          <div 
            className="fixed inset-y-0 right-0 pointer-events-none z-40 flex items-center justify-end pr-6"
            style={{ 
              width: `${Math.max(80, swipeProgress * 160)}px`,
              background: `linear-gradient(to left, rgba(239, 68, 68, ${Math.min(swipeProgress * 0.85, 0.85)}), transparent)`,
            }}
          >
            <div 
              className="flex items-center gap-1 text-white font-bold drop-shadow-lg"
              style={{ opacity: Math.min(swipeProgress * 1.5, 1), transform: `scale(${1 + swipeProgress * 0.3})` }}
            >
              <X className="h-10 w-10" strokeWidth={3} />
            </div>
          </div>
        )}

        {!track ? (
          <Card className="w-full max-w-md">
            <CardContent className="p-8 text-center space-y-4">
              <Music className="h-16 w-16 mx-auto text-muted-foreground" />
              <div className="space-y-2">
                <h2 className="text-xl font-semibold">No Track Playing</h2>
                <p className="text-muted-foreground">
                  Open Spotify and start playing music from a playlist to begin testing.
                </p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <>
            <div 
              {...swipeHandlers}
              className={`w-full max-w-md space-y-1 sm:space-y-4 pb-16 sm:pb-0 transition-transform duration-200 ${
                swipeDirection === 'right' ? 'translate-x-2' : 
                swipeDirection === 'left' ? '-translate-x-2' : 
                showSwipeNudge ? 'animate-swipe-nudge' : ''
              }`}
              style={{ touchAction: isMobile ? 'pan-x' : 'auto' }}
            >
              {/* Desktop only: Like button at top */}
              <Button
                size="lg"
                className="hidden sm:flex w-full py-6 rounded-xl text-lg gap-3"
                onClick={() => likeMutation.mutate()}
                disabled={isActionPending}
                data-testid="button-like-desktop"
              >
                <ThumbsUp className="h-7 w-7" />
                Like
              </Button>

              <Card className="overflow-hidden relative">
                <div className="relative">
                  {albumArt && (
                    <div className="w-full max-h-[28vh] sm:max-h-[50vh] overflow-hidden flex items-center justify-center bg-black/10">
                      <img
                        src={albumArt}
                        alt={track.album.name}
                        className="w-full h-auto object-contain max-h-[28vh] sm:max-h-[50vh]"
                      />
                    </div>
                  )}
                  <div 
                    className={`absolute bottom-0 left-0 right-0 h-1 bg-black/30 ${!isMobile ? 'cursor-pointer group' : ''}`}
                    onClick={(e) => {
                      if (isMobile) return;
                      const rect = e.currentTarget.getBoundingClientRect();
                      const clickX = e.clientX - rect.left;
                      const percent = clickX / rect.width;
                      const newPosition = Math.floor(percent * durationMs);
                      seekMutation.mutate(newPosition);
                    }}
                    data-testid="progress-bar-container"
                  >
                    <div 
                      className={`h-full bg-primary transition-all duration-300 ${!isMobile ? 'group-hover:bg-primary/80' : ''}`}
                      style={{ width: `${progressPercent}%` }}
                      data-testid="progress-bar"
                    />
                    {!isMobile && (
                      <div 
                        className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-md opacity-0 group-hover:opacity-100 transition-opacity"
                        style={{ left: `calc(${progressPercent}% - 6px)` }}
                      />
                    )}
                  </div>
                </div>
                <CardContent className="p-3 sm:p-6 space-y-1 sm:space-y-3">
                  <div className="space-y-0.5">
                    <h2 className="text-sm sm:text-xl font-semibold truncate" data-testid="text-track-name">
                      {track.name}
                    </h2>
                    <p className="text-xs sm:text-base text-muted-foreground truncate" data-testid="text-artist-name">
                      {artistNames}
                    </p>
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground font-mono">
                    <span data-testid="text-progress">{formatTime(progressMs)}</span>
                    <span data-testid="text-duration">{formatTime(durationMs)}</span>
                  </div>
                  <div className="flex items-center justify-center gap-2 sm:gap-3">
                    <Button
                      size="sm"
                      variant="ghost"
                      className={`rounded-full ${shuffleData?.shuffle_state ? 'text-primary' : ''}`}
                      onClick={() => shuffleMutation.mutate(!shuffleData?.shuffle_state)}
                      disabled={shuffleMutation.isPending}
                      data-testid="button-shuffle"
                    >
                      <Shuffle className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="rounded-full"
                      onClick={() => previousMutation.mutate()}
                      disabled={isPlaybackPending}
                      data-testid="button-previous"
                    >
                      <SkipBack className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="outline"
                      className="rounded-full"
                      onClick={() => isPlaying ? pauseMutation.mutate() : playMutation.mutate()}
                      disabled={isPlaybackPending}
                      data-testid="button-play-pause"
                    >
                      {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5 ml-0.5" />}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="rounded-full"
                      onClick={() => skipMutation.mutate()}
                      disabled={isPlaybackPending}
                      data-testid="button-skip"
                    >
                      <SkipForward className="h-4 w-4" />
                    </Button>
                    <div className="w-8" />
                  </div>
                  {playbackState?.context?.type === "playlist" && playbackState.context.name && (
                    <div className="flex items-center gap-1 pt-1 border-t text-xs text-muted-foreground">
                      <ListMusic className="h-3 w-3 shrink-0" />
                      <span className="truncate" data-testid="text-playlist-name">
                        {playbackState.context.name}
                      </span>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Desktop only: Dislike button below card */}
              <Button
                size="lg"
                variant="destructive"
                className="hidden sm:flex w-full py-6 rounded-xl text-lg gap-3"
                onClick={() => dislikeMutation.mutate()}
                disabled={isActionPending}
                data-testid="button-dislike-desktop"
              >
                <ThumbsDown className="h-7 w-7" />
                Dislike
              </Button>

              {Array.isArray(targetPlaylists) && targetPlaylists.length === 0 && (
                <p className="text-center text-xs sm:text-sm text-amber-600 dark:text-amber-400 hidden sm:block">
                  No target playlists set. Tap the settings icon to add one.
                </p>
              )}

              {!isMobile && (
                <p className="text-center text-xs text-muted-foreground/60 pt-2">
                  Ctrl+Shift+Enter to like, Ctrl+Shift+Delete to dislike
                </p>
              )}
            </div>

            {/* Mobile only: Fixed bottom action bar - Dislike left (swipe left), Like right (swipe right) */}
            <div className="fixed bottom-0 left-0 right-0 p-3 bg-background/95 backdrop-blur border-t flex gap-3 sm:hidden z-50">
              <Button
                size="lg"
                variant="destructive"
                className="flex-1 rounded-xl gap-2"
                onClick={() => dislikeMutation.mutate()}
                disabled={isActionPending}
                data-testid="button-dislike"
              >
                <ThumbsDown className="h-5 w-5" />
                Dislike
              </Button>
              <Button
                size="lg"
                className="flex-1 rounded-xl gap-2"
                onClick={() => likeMutation.mutate()}
                disabled={isActionPending}
                data-testid="button-like"
              >
                <ThumbsUp className="h-5 w-5" />
                Like
              </Button>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
