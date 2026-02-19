# YouTube Skill — Command Reference

Full flag reference for `scripts/yt.py`. See [SKILL.md](SKILL.md) for setup and agent instructions.

---

## Channel

```bash
python3 scripts/yt.py whoami
```

Output: channel name, ID, handle, subscriber count, total video count, total views, country.

---

## Videos

### List videos

```bash
python3 scripts/yt.py videos list                        # most recent 50 (default)
python3 scripts/yt.py videos list --limit 200
python3 scripts/yt.py videos list --status public
python3 scripts/yt.py videos list --status private
python3 scripts/yt.py videos list --status unlisted
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

Upload is resumable — progress is shown as a percentage. If interrupted, restart the same command within 24 hours and the API resumes from where it stopped.

Supported formats: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, `.flv`, `.wmv`, `.m4v`.

### Update video metadata

```bash
python3 scripts/yt.py videos update <VIDEO_ID> --title "New Title"
python3 scripts/yt.py videos update <VIDEO_ID> --description "Updated description"
python3 scripts/yt.py videos update <VIDEO_ID> --tags "tag1,tag2,tag3"
python3 scripts/yt.py videos update <VIDEO_ID> --category 28
python3 scripts/yt.py videos update <VIDEO_ID> --privacy public
python3 scripts/yt.py videos update <VIDEO_ID> --privacy private
python3 scripts/yt.py videos update <VIDEO_ID> --publish-at "2025-06-01T12:00:00Z"

# Multiple fields at once
python3 scripts/yt.py videos update <VIDEO_ID> \
  --title "Final Title" \
  --description "SEO-optimised description" \
  --tags "keyword1,keyword2" \
  --category 28 \
  --privacy public
```

Only provided flags are changed — all other fields keep their existing values.

### Set a custom thumbnail

```bash
python3 scripts/yt.py videos thumbnail <VIDEO_ID> thumbnail.jpg
```

Requirements: JPG or PNG, max 2 MB, 1280×720 px (16:9) recommended. Custom thumbnails require a verified YouTube account.

### Delete a video

```bash
python3 scripts/yt.py videos delete <VIDEO_ID>          # prompts for confirmation
python3 scripts/yt.py videos delete <VIDEO_ID> --yes    # skip confirmation
```

Deletion is permanent and cannot be undone.

---

## Playlists

```bash
# List all playlists
python3 scripts/yt.py playlists list
python3 scripts/yt.py playlists list --format json

# Create
python3 scripts/yt.py playlists create "My New Playlist"
python3 scripts/yt.py playlists create "Tutorial Series" \
  --description "Step-by-step tutorials" \
  --privacy public

# List videos in a playlist
python3 scripts/yt.py playlists items <PLAYLIST_ID>
python3 scripts/yt.py playlists items <PLAYLIST_ID> --format json

# Add / remove videos
python3 scripts/yt.py playlists add <PLAYLIST_ID> <VIDEO_ID>
python3 scripts/yt.py playlists remove <PLAYLIST_ID> <VIDEO_ID>

# Delete a playlist (videos are NOT deleted)
python3 scripts/yt.py playlists delete <PLAYLIST_ID>
python3 scripts/yt.py playlists delete <PLAYLIST_ID> --yes
```

---

## Comments

```bash
# List top-level comments (default: top 20 by relevance)
python3 scripts/yt.py comments list <VIDEO_ID>
python3 scripts/yt.py comments list <VIDEO_ID> --limit 50 --order time
python3 scripts/yt.py comments list <VIDEO_ID> --format json

# Reply to a comment thread
python3 scripts/yt.py comments reply <COMMENT_THREAD_ID> "Thanks for watching!"
```

The thread ID is shown in brackets `[...]` in the `comments list` output. Confirm reply text with the user before posting — replies are public and immediate.

---

## Search

Searches only your own channel's content.

```bash
python3 scripts/yt.py search "python tutorial"
python3 scripts/yt.py search "cooking" --limit 20
python3 scripts/yt.py search "series" --type playlist
python3 scripts/yt.py search "tips" --format json
```

---

## Export & Bulk Operations

```bash
# Export all channel videos to CSV
python3 scripts/yt.py export > my_channel.csv

# JSON format
python3 scripts/yt.py export --format json > my_channel.json

# Bulk-update metadata from a CSV file
python3 scripts/yt.py bulk-update updates.csv
```

CSV columns for export: `id`, `title`, `description`, `tags` (pipe-separated), `category_id`, `published_at`, `status`, `duration`, `views`, `likes`, `comments`, `url`.

For bulk-update: edit any field, leave cells blank to preserve existing values. The `id` column must be present and unchanged.

---

## Common Workflows

### Publish a new video

```bash
# 1. Upload (stays private)
python3 scripts/yt.py videos upload recording.mp4 \
  --title "Episode 12 — Deep Dive" \
  --description "In this episode we explore..." \
  --tags "podcast,tech,deepdive" \
  --category 28

# 2. Set thumbnail (note the VIDEO_ID printed after upload)
python3 scripts/yt.py videos thumbnail <VIDEO_ID> thumbnail.jpg

# 3. Add to playlist
python3 scripts/yt.py playlists add <PLAYLIST_ID> <VIDEO_ID>

# 4a. Publish immediately
python3 scripts/yt.py videos update <VIDEO_ID> --privacy public

# 4b. Or schedule for later
python3 scripts/yt.py videos update <VIDEO_ID> --publish-at "2025-06-01T14:00:00Z"
```

### SEO metadata bulk update

```bash
python3 scripts/yt.py export > catalogue.csv
# Edit titles, descriptions, and tags in catalogue.csv (any spreadsheet)
python3 scripts/yt.py bulk-update catalogue.csv
```

### Organise videos into playlists

```bash
python3 scripts/yt.py videos list --format csv > all_videos.csv
python3 scripts/yt.py playlists create "Tutorial Series 2025" --privacy public
python3 scripts/yt.py playlists add <PLAYLIST_ID> <VIDEO_ID_1>
python3 scripts/yt.py playlists add <PLAYLIST_ID> <VIDEO_ID_2>
```

### Audit channel stats

```bash
python3 scripts/yt.py whoami                        # channel summary
python3 scripts/yt.py videos list --limit 50        # top 50 by recency with views
python3 scripts/yt.py export > audit.csv            # full export for spreadsheet analysis
```

### Schedule a video series

```bash
python3 scripts/yt.py videos update <VIDEO_ID_1> --privacy private --publish-at "2025-07-01T14:00:00Z"
python3 scripts/yt.py videos update <VIDEO_ID_2> --privacy private --publish-at "2025-07-08T14:00:00Z"
python3 scripts/yt.py videos update <VIDEO_ID_3> --privacy private --publish-at "2025-07-15T14:00:00Z"
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
import sys; sys.path.insert(0, 'scripts')
import yt; svc = yt.get_service()
r = svc.videoCategories().list(part='snippet', regionCode='US').execute()
for c in r['items']: print(c['id'], c['snippet']['title'])
"
```

---

## API Quota Reference

Default quota: **10,000 units per day** (resets at midnight Pacific Time).

| Operation | Cost |
|-----------|------|
| Upload a video | 1,600 units |
| Update metadata | 50 units |
| Set thumbnail | 50 units |
| Search query | 100 units |
| List videos (per page of 50) | 1 unit |
| Get video details | 1 unit |
| List comments (per page) | 1 unit |

If the quota is exhausted the API returns HTTP 403 `quotaExceeded`. Wait until midnight PT or request a quota increase in Google Cloud Console.

---

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `quotaExceeded` (403) | Daily API quota exhausted | Wait until midnight Pacific Time or request a quota increase in Cloud Console |
| `forbidden` (403) on thumbnail | Account not verified | Verify at youtube.com/verify |
| `videoNotFound` (404) | Wrong video ID | Run `videos list` to find the correct ID |
| `uploadLimitExceeded` | Daily upload limit hit | Unverified accounts are limited to 15-min videos; verify your account |
| `invalid` on `--schedule` or `--publish-at` | Wrong datetime format | Use ISO 8601 UTC: `2025-12-31T18:00:00Z` |
| Token file missing | Credentials deleted or corrupted | Run `python3 scripts/yt.py auth` to re-authorise |
| `Missing dependencies` | Python packages not installed | Run `bash scripts/setup.sh` |
| Browser does not open | Headless / remote environment | Copy the URL printed to stderr and open it manually |
