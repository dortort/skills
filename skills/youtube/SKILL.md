---
name: youtube
description: Manages YouTube channels and videos using the YouTube Data API v3. Handles OAuth2 authentication, video uploads with resumable transfer, metadata updates, thumbnail setting, playlist management, comment moderation, channel-wide search, and bulk CSV workflows. Use when the user wants to upload a video, manage their YouTube channel, update video titles or descriptions, create or manage playlists, list channel videos, search their content, export a video catalogue, or bulk-edit metadata. Trigger phrases include "youtube", "upload video", "channel manager", "my videos", "YouTube playlist", "YouTube API", "update metadata".
user-invocable: true
disable-model-invocation: true
argument-hint: "<intent>"
---

# YouTube — Creator & Channel Manager

Manages YouTube channels and videos via the YouTube Data API v3, using the `scripts/yt.py` helper and the official `google-api-python-client` SDK. All operations are authenticated with OAuth2 and credentials are cached after the first authorisation.

## Input Format

```
/youtube <intent>
```

Describe what you want to do in plain language. Examples:

- `/youtube upload my-video.mp4 with title "Product Launch"`
- `/youtube list all public videos`
- `/youtube update dQw4w9WgXcQ — set title to "New Title" and tags to "tutorial,tips"`
- `/youtube export channel to CSV`
- `/youtube bulk update metadata from updates.csv`

---

## Prerequisites

- Python 3.8 or higher
- pip
- A Google account with a YouTube channel
- A Google Cloud project with the YouTube Data API v3 enabled (one-time setup)

---

## Authentication

Authentication is fluid: run setup once and all subsequent operations are silent.

### One-time setup

**Step 1 — Install dependencies**

```bash
bash scripts/setup.sh
```

This installs `google-api-python-client`, `google-auth-httplib2`, and `google-auth-oauthlib`, and creates `~/.youtube-skill/`.

**Step 2 — Create Google Cloud credentials**

1. Go to [https://console.cloud.google.com](https://console.cloud.google.com) and create or select a project
2. Navigate to **APIs & Services → Library**, search for **YouTube Data API v3**, and enable it
3. Navigate to **APIs & Services → Credentials**
4. Click **Create Credentials → OAuth 2.0 Client ID**, choose **Desktop app**, click **Create**
5. Click **Download JSON** and save the file as:

```
~/.youtube-skill/client_secrets.json
```

**Step 3 — Authorise**

```bash
python3 scripts/yt.py auth
```

A browser window opens automatically. Sign in and grant access. Credentials are cached at `~/.youtube-skill/credentials.json` and silently refreshed on subsequent runs.

### Re-authentication

Token refresh is automatic. To force a fresh login (e.g. after revoking access):

```bash
rm ~/.youtube-skill/credentials.json
python3 scripts/yt.py auth
```

---

## Channel Info

**Show the authenticated channel:**

```bash
python3 scripts/yt.py whoami
```

Output: channel name, ID, handle, subscriber count, total views, country.

---

## Videos

### List videos

```bash
# Most recent 50 videos (default)
python3 scripts/yt.py videos list

# Custom limit
python3 scripts/yt.py videos list --limit 200

# Filter by status
python3 scripts/yt.py videos list --status public
python3 scripts/yt.py videos list --status private
python3 scripts/yt.py videos list --status unlisted

# Output formats
python3 scripts/yt.py videos list --format csv
python3 scripts/yt.py videos list --format json
```

### Get video details

```bash
python3 scripts/yt.py videos get <VIDEO_ID>
python3 scripts/yt.py videos get <VIDEO_ID> --format json
```

Output: title, ID, URL, privacy status, publish date, duration, views, likes, comments, category, tags, description.

### Upload a video

```bash
# Minimal — uploads as private (safe default)
python3 scripts/yt.py videos upload path/to/video.mp4

# Full metadata
python3 scripts/yt.py videos upload path/to/video.mp4 \
  --title "My Awesome Video" \
  --description "Full description here" \
  --tags "tutorial,tips,howto" \
  --category 27 \
  --privacy private

# Schedule for future publication (video stays private until then)
python3 scripts/yt.py videos upload path/to/video.mp4 \
  --title "Scheduled Video" \
  --privacy private \
  --schedule "2025-12-31T18:00:00Z"
```

Upload is resumable — progress is shown as a percentage. If interrupted, restart the command; the API will resume from where it stopped if the session is still valid (within 24 hours).

**After upload**, the script prints the video ID and suggested next steps (set thumbnail, update metadata, publish).

### Update video metadata

```bash
# Update title only
python3 scripts/yt.py videos update <VIDEO_ID> --title "New Title"

# Update description
python3 scripts/yt.py videos update <VIDEO_ID> --description "Updated description"

# Replace all tags
python3 scripts/yt.py videos update <VIDEO_ID> --tags "tag1,tag2,tag3"

# Change privacy
python3 scripts/yt.py videos update <VIDEO_ID> --privacy public
python3 scripts/yt.py videos update <VIDEO_ID> --privacy private

# Schedule a publish time (video becomes public at that UTC datetime)
python3 scripts/yt.py videos update <VIDEO_ID> --publish-at "2025-06-01T12:00:00Z"

# Multiple fields at once
python3 scripts/yt.py videos update <VIDEO_ID> \
  --title "Final Title" \
  --description "SEO-optimised description" \
  --tags "keyword1,keyword2" \
  --category 28 \
  --privacy public
```

Only provided flags are changed; all other fields keep their existing values.

### Set a custom thumbnail

```bash
python3 scripts/yt.py videos thumbnail <VIDEO_ID> thumbnail.jpg
```

Requirements: JPG or PNG, max 2 MB, 1280×720 px (16:9) recommended. Custom thumbnails require a verified YouTube account.

### Delete a video

```bash
python3 scripts/yt.py videos delete <VIDEO_ID>
# Skip confirmation prompt
python3 scripts/yt.py videos delete <VIDEO_ID> --yes
```

Deletion is permanent and cannot be undone.

---

## Playlists

### List playlists

```bash
python3 scripts/yt.py playlists list
python3 scripts/yt.py playlists list --format json
```

### Create a playlist

```bash
python3 scripts/yt.py playlists create "My New Playlist"
python3 scripts/yt.py playlists create "Tutorial Series" \
  --description "Step-by-step tutorials" \
  --privacy public
```

### List videos in a playlist

```bash
python3 scripts/yt.py playlists items <PLAYLIST_ID>
python3 scripts/yt.py playlists items <PLAYLIST_ID> --format json
```

### Add a video to a playlist

```bash
python3 scripts/yt.py playlists add <PLAYLIST_ID> <VIDEO_ID>
```

### Remove a video from a playlist

```bash
python3 scripts/yt.py playlists remove <PLAYLIST_ID> <VIDEO_ID>
```

### Delete a playlist

```bash
python3 scripts/yt.py playlists delete <PLAYLIST_ID>
python3 scripts/yt.py playlists delete <PLAYLIST_ID> --yes
```

Deleting a playlist does not delete the videos in it.

---

## Comments

### List comments

```bash
# Top 20 by relevance (default)
python3 scripts/yt.py comments list <VIDEO_ID>

# More comments, newest first
python3 scripts/yt.py comments list <VIDEO_ID> --limit 50 --order time

# JSON for programmatic use
python3 scripts/yt.py comments list <VIDEO_ID> --format json
```

The thread ID printed in brackets is used when replying.

### Reply to a comment

```bash
python3 scripts/yt.py comments reply <COMMENT_THREAD_ID> "Thanks for watching!"
```

---

## Search

Search your own channel's content:

```bash
python3 scripts/yt.py search "python tutorial"
python3 scripts/yt.py search "cooking" --limit 20
python3 scripts/yt.py search "series" --type playlist
python3 scripts/yt.py search "tips" --format json
```

---

## Export & Bulk Operations

### Export all videos to CSV

```bash
# Export to stdout (redirect to file)
python3 scripts/yt.py export > my_channel.csv

# JSON format
python3 scripts/yt.py export --format json > my_channel.json
```

CSV columns: `id`, `title`, `description`, `tags` (pipe-separated), `category_id`, `published_at`, `status`, `duration`, `views`, `likes`, `comments`, `url`.

### Bulk-update metadata from CSV

1. Export the channel catalogue:

   ```bash
   python3 scripts/yt.py export > updates.csv
   ```

2. Open `updates.csv` in a spreadsheet and edit any fields: `title`, `description`, `tags`, `category_id`, `status`. Leave cells blank for fields you do not want to change. The `id` column must be present and unchanged.

3. Apply the updates:

   ```bash
   python3 scripts/yt.py bulk-update updates.csv
   ```

   The script reads only non-empty cells, fetches current metadata in batches, applies changes, and reports each update.

---

## Common Workflows

### Workflow: Publish a new video

```bash
# 1. Upload (stays private)
python3 scripts/yt.py videos upload recording.mp4 \
  --title "Episode 12 — Deep Dive" \
  --description "In this episode we explore..." \
  --tags "podcast,tech,deepdive" \
  --category 28

# Note the VIDEO_ID printed after upload

# 2. Set thumbnail
python3 scripts/yt.py videos thumbnail <VIDEO_ID> thumbnail.jpg

# 3. Add to playlist
python3 scripts/yt.py playlists add <PLAYLIST_ID> <VIDEO_ID>

# 4. Publish immediately
python3 scripts/yt.py videos update <VIDEO_ID> --privacy public

# — or schedule for later —
python3 scripts/yt.py videos update <VIDEO_ID> --publish-at "2025-06-01T14:00:00Z"
```

### Workflow: SEO metadata bulk update

```bash
# 1. Export current state
python3 scripts/yt.py export > catalogue.csv

# 2. Edit titles, descriptions, and tags in catalogue.csv

# 3. Apply
python3 scripts/yt.py bulk-update catalogue.csv
```

### Workflow: Organise videos into playlists

```bash
# List all videos and pick IDs to group
python3 scripts/yt.py videos list --format csv > all_videos.csv

# Create a new playlist
python3 scripts/yt.py playlists create "Tutorial Series 2025" --privacy public

# Add videos one by one
python3 scripts/yt.py playlists add <PLAYLIST_ID> <VIDEO_ID_1>
python3 scripts/yt.py playlists add <PLAYLIST_ID> <VIDEO_ID_2>
```

### Workflow: Audit channel stats

```bash
# Full export with view counts
python3 scripts/yt.py export > audit.csv

# Quick top-50 with view counts in table format
python3 scripts/yt.py videos list --limit 50

# Channel-level summary
python3 scripts/yt.py whoami
```

### Workflow: Schedule a video series

```bash
# Upload each episode as private, then schedule them
for i in 1 2 3; do
  python3 scripts/yt.py videos update <VIDEO_ID_$i> \
    --privacy private \
    --publish-at "2025-07-0${i}T14:00:00Z"
done
```

---

## Video Category IDs

| ID | Category |
|----|----------|
| 1  | Film & Animation |
| 2  | Autos & Vehicles |
| 10 | Music |
| 15 | Pets & Animals |
| 17 | Sports |
| 19 | Travel & Events |
| 20 | Gaming |
| 22 | People & Blogs (default) |
| 23 | Comedy |
| 24 | Entertainment |
| 25 | News & Politics |
| 26 | Howto & Style |
| 27 | Education |
| 28 | Science & Technology |
| 29 | Nonprofits & Activism |

Fetch the current list for your region:

```bash
python3 -c "
import scripts.yt as yt
svc = yt.get_service()
r = svc.videoCategories().list(part='snippet', regionCode='US').execute()
for c in r['items']:
    print(c['id'], c['snippet']['title'])
"
```

---

## API Quota Reference

The YouTube Data API v3 has a default quota of **10,000 units per day**.

| Operation | Cost |
|-----------|------|
| Upload a video | 1,600 units |
| Update metadata | 50 units |
| List videos (per page of 50) | 1 unit |
| Get video details | 1 unit |
| Set thumbnail | 50 units |
| Search query | 100 units |
| List comments (per page) | 1 unit |

Quota resets at midnight Pacific Time. If you hit the limit, the API returns an HTTP 403 with `quotaExceeded`; wait until midnight PT or request a quota increase in Google Cloud Console.

---

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `quotaExceeded` (403) | Daily API quota exhausted | Wait until midnight Pacific Time or request a quota increase |
| `forbidden` (403) on thumbnail | Account not verified | Verify your YouTube account at youtube.com/verify |
| `videoNotFound` (404) | Wrong video ID | Run `videos list` to find the correct ID |
| `uploadLimitExceeded` | Daily upload limit hit | YouTube limits unverified accounts to 15 min videos; verify your account |
| `invalid` on `--schedule` | Wrong datetime format | Use ISO 8601 UTC: `2025-12-31T18:00:00Z` |
| Token file missing | Credentials deleted or corrupted | Run `python3 scripts/yt.py auth` to re-authorise |
| `Missing dependencies` | Python packages not installed | Run `bash scripts/setup.sh` |
| Browser does not open | Headless environment | Copy the URL printed to stderr and open it manually |
