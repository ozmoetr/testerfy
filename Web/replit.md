# Testerfy - Spotify Music Testing App

## Overview
Testerfy is a Spotify companion app for testing new music. Users can quickly like or dislike songs while listening to a playlist, and the app will automatically manage playlists based on their decisions.

## Features
- **Spotify OAuth Login**: Authenticate with your Spotify account
- **Like/Dislike Actions**:
  - **Like**: Saves the current song to all configured target playlists, removes it from the current playlist, and skips to the next song
  - **Dislike**: Removes the current song from the current playlist and skips to the next song
- **Target Playlist Configuration**: Choose which playlists liked songs should be saved to
- **Dark/Light Theme**: Toggle between themes

## Required Environment Variables

### Secrets (Required for Spotify Integration)
- `SPOTIFY_CLIENT_ID` - Your Spotify app client ID
- `SPOTIFY_CLIENT_SECRET` - Your Spotify app client secret
- `SESSION_SECRET` - Secret for session encryption (already configured)

### Environment Variables (Auto-configured)
- `DATABASE_URL` - PostgreSQL connection string (auto-provided by Replit)
- `SPOTIFY_REDIRECT_URI` - OAuth callback URL (defaults to your Replit URL + `/api/auth/callback`)

## Setup Instructions
1. Go to https://developer.spotify.com/dashboard
2. Create a new app named "Testerfy"
3. Set the Redirect URI to: `https://[your-replit-url]/api/auth/callback`
4. Check "Web API" and "Web Playback SDK"
5. Copy the Client ID and Client Secret
6. Add them as secrets in Replit

## Project Structure
- `client/` - React frontend with Vite
- `server/` - Express backend
- `shared/` - Shared types and API contracts

## API Endpoints
- `GET /api/auth/login` - Initiate Spotify OAuth
- `GET /api/auth/callback` - OAuth callback handler
- `POST /api/auth/logout` - Logout user
- `GET /api/auth/me` - Get current user
- `GET /api/playlists` - List user's Spotify playlists
- `GET /api/target-playlists` - List configured target playlists
- `POST /api/target-playlists` - Add a target playlist
- `DELETE /api/target-playlists/:id` - Remove a target playlist
- `GET /api/player/current` - Get current playback state
- `POST /api/player/like` - Like current song
- `POST /api/player/dislike` - Dislike current song
- `POST /api/player/skip` - Skip to next song
