#!/usr/bin/env python3
"""YouTube Creator CLI — YouTube Data API v3 wrapper for creators and channel managers.

Usage:
  yt.py auth                                      Set up or refresh OAuth2 credentials
  yt.py whoami                                    Show authenticated channel info

  yt.py videos list   [--limit N] [--status S] [--format table|csv|json]
  yt.py videos get    <VIDEO_ID> [--format table|json]
  yt.py videos upload <FILE> [--title T] [--description D] [--tags T] [--category ID]
                             [--privacy public|private|unlisted] [--schedule ISO8601]
  yt.py videos update <VIDEO_ID> [--title T] [--description D] [--tags T]
                                 [--category ID] [--privacy S] [--publish-at ISO8601]
  yt.py videos delete <VIDEO_ID> [--yes]
  yt.py videos thumbnail <VIDEO_ID> <IMAGE>

  yt.py playlists list   [--format table|json]
  yt.py playlists create <TITLE> [--description D] [--privacy public|private|unlisted]
  yt.py playlists items  <PLAYLIST_ID> [--format table|json]
  yt.py playlists add    <PLAYLIST_ID> <VIDEO_ID>
  yt.py playlists remove <PLAYLIST_ID> <VIDEO_ID>
  yt.py playlists delete <PLAYLIST_ID> [--yes]

  yt.py comments list  <VIDEO_ID> [--limit N] [--order relevance|time] [--format table|json]
  yt.py comments reply <COMMENT_ID> <TEXT>

  yt.py search <QUERY> [--limit N] [--type video|playlist|channel] [--format table|json]

  yt.py export      [--format csv|json]
  yt.py bulk-update <CSV_FILE>
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

# ── Credentials paths ──────────────────────────────────────────────────────────
CREDENTIALS_DIR = Path.home() / ".youtube-skill"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"
CLIENT_SECRETS_FILE = CREDENTIALS_DIR / "client_secrets.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

# ── Auth ───────────────────────────────────────────────────────────────────────

def _check_deps():
    try:
        import googleapiclient  # noqa: F401
        import google.auth  # noqa: F401
        import google_auth_oauthlib  # noqa: F401
    except ImportError:
        print("Missing dependencies. Run:  bash scripts/setup.sh", file=sys.stderr)
        sys.exit(1)


def get_service():
    """Return an authenticated YouTube Data API v3 service object.

    On first call: opens a browser window for OAuth2 consent and caches the token.
    On subsequent calls: loads the cached token, refreshing silently if needed.
    """
    _check_deps()
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None

    if CREDENTIALS_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(CREDENTIALS_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing credentials...", file=sys.stderr)
            creds.refresh(Request())
        else:
            if not CLIENT_SECRETS_FILE.exists():
                print(
                    f"\nNo OAuth credentials found at:\n  {CLIENT_SECRETS_FILE}\n",
                    file=sys.stderr,
                )
                print(
                    "Run setup first:\n  bash scripts/setup.sh\n"
                    "or follow the manual steps in SKILL.md under 'Authentication'.",
                    file=sys.stderr,
                )
                sys.exit(1)

            print("Opening browser for YouTube authorisation...", file=sys.stderr)
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRETS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0, open_browser=True)
            print("Authorisation successful.", file=sys.stderr)

        CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        CREDENTIALS_FILE.write_text(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def _my_channel(youtube):
    resp = youtube.channels().list(part="id,snippet,contentDetails,statistics", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        print("No YouTube channel found for this account.", file=sys.stderr)
        sys.exit(1)
    return items[0]


def _my_channel_id(youtube):
    return _my_channel(youtube)["id"]


def _uploads_playlist_id(youtube, channel_id=None):
    cid = channel_id or _my_channel_id(youtube)
    resp = youtube.channels().list(part="contentDetails", id=cid).execute()
    return resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def _paginate(method, params, *, key="items", limit=None):
    """Yield all items across paginated API responses, up to limit."""
    collected = []
    next_page = None
    while True:
        if next_page:
            params = {**params, "pageToken": next_page}
        resp = method(**params).execute()
        batch = resp.get(key, [])
        collected.extend(batch)
        next_page = resp.get("nextPageToken")
        if not next_page or (limit is not None and len(collected) >= limit):
            break
    return collected[:limit] if limit else collected


def _fetch_video_details(youtube, video_ids, part="snippet,status,statistics,contentDetails"):
    """Batch-fetch video details for up to 50 IDs at a time."""
    details = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        resp = youtube.videos().list(part=part, id=",".join(batch)).execute()
        for item in resp.get("items", []):
            details[item["id"]] = item
    return details


# ── whoami ─────────────────────────────────────────────────────────────────────

def cmd_auth(args, youtube):
    ch = _my_channel(youtube)
    s = ch["snippet"]
    st = ch.get("statistics", {})
    print(f"Authenticated as: {s['title']}")
    print(f"Channel ID:       {ch['id']}")
    print(f"Subscribers:      {st.get('subscriberCount', 'hidden')}")
    print(f"Credentials:      {CREDENTIALS_FILE}")


def cmd_whoami(args, youtube):
    ch = _my_channel(youtube)
    s = ch["snippet"]
    st = ch.get("statistics", {})
    cd = ch.get("contentDetails", {})
    print(f"Channel:     {s['title']}")
    print(f"ID:          {ch['id']}")
    print(f"Handle:      @{s.get('customUrl', '').lstrip('@')}")
    print(f"Subscribers: {st.get('subscriberCount', 'hidden')}")
    print(f"Videos:      {st.get('videoCount', '?')}")
    print(f"Views:       {st.get('viewCount', '?')}")
    print(f"Country:     {s.get('country', 'not set')}")
    print(f"URL:         https://youtube.com/channel/{ch['id']}")


# ── videos list ────────────────────────────────────────────────────────────────

def cmd_videos_list(args, youtube):
    uploads_id = _uploads_playlist_id(youtube)
    limit = args.limit or 50

    items = _paginate(
        youtube.playlistItems().list,
        dict(part="snippet,contentDetails", playlistId=uploads_id, maxResults=min(50, limit)),
        limit=limit,
    )

    video_ids = [v["contentDetails"]["videoId"] for v in items]
    details = _fetch_video_details(youtube, video_ids, part="snippet,status,statistics")

    if args.status:
        video_ids = [
            vid for vid in video_ids
            if details.get(vid, {}).get("status", {}).get("privacyStatus") == args.status
        ]

    rows = []
    for vid_id in video_ids:
        d = details.get(vid_id, {})
        s = d.get("snippet", {})
        st = d.get("status", {})
        stats = d.get("statistics", {})
        rows.append({
            "id": vid_id,
            "title": s.get("title", "(deleted)"),
            "published": (s.get("publishedAt") or "")[:10],
            "status": st.get("privacyStatus", "?"),
            "views": stats.get("viewCount", "?"),
            "likes": stats.get("likeCount", "?"),
            "comments": stats.get("commentCount", "?"),
            "url": f"https://youtu.be/{vid_id}",
        })

    fmt = getattr(args, "format", "table")
    if fmt == "json":
        print(json.dumps(rows, indent=2))
    elif fmt == "csv":
        if rows:
            writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    else:
        for r in rows:
            title = r["title"][:52]
            views = str(r["views"]).rjust(9)
            print(f"{r['id']}  {r['status']:9}  {views} views  {r['published']}  {title}")


# ── videos get ─────────────────────────────────────────────────────────────────

def cmd_videos_get(args, youtube):
    resp = youtube.videos().list(
        part="snippet,status,statistics,contentDetails,localizations",
        id=args.video_id,
    ).execute()
    items = resp.get("items", [])
    if not items:
        print(f"Video not found: {args.video_id}", file=sys.stderr)
        sys.exit(1)

    item = items[0]
    fmt = getattr(args, "format", "table")
    if fmt == "json":
        print(json.dumps(item, indent=2))
        return

    s = item["snippet"]
    st = item["status"]
    stats = item.get("statistics", {})
    cd = item.get("contentDetails", {})
    print(f"Title:        {s['title']}")
    print(f"ID:           {item['id']}")
    print(f"URL:          https://youtu.be/{item['id']}")
    print(f"Status:       {st['privacyStatus']}")
    publish = s.get("publishedAt", "not published")
    scheduled = st.get("publishAt")
    if scheduled:
        publish = f"scheduled for {scheduled}"
    print(f"Published:    {publish}")
    print(f"Duration:     {cd.get('duration', '?')}")
    print(f"Views:        {stats.get('viewCount', '?')}")
    print(f"Likes:        {stats.get('likeCount', '?')}")
    print(f"Comments:     {stats.get('commentCount', '?')}")
    print(f"Category ID:  {s.get('categoryId', '?')}")
    tags = s.get("tags", [])
    print(f"Tags ({len(tags)}):   {', '.join(tags[:8])}{'...' if len(tags) > 8 else ''}")
    print(f"\nDescription:\n{s.get('description', '(none)')}")


# ── videos upload ──────────────────────────────────────────────────────────────

def cmd_videos_upload(args, youtube):
    from googleapiclient.http import MediaFileUpload

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    title = args.title or file_path.stem
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else []

    body = {
        "snippet": {
            "title": title,
            "description": args.description or "",
            "tags": tags,
            "categoryId": args.category or "22",  # 22 = People & Blogs
        },
        "status": {
            "privacyStatus": args.privacy or "private",
            "selfDeclaredMadeForKids": False,
        },
    }

    if args.schedule:
        body["status"]["publishAt"] = args.schedule
        body["status"]["privacyStatus"] = "private"

    # Detect MIME type
    ext = file_path.suffix.lower()
    mime_map = {
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
        ".flv": "video/x-flv",
        ".wmv": "video/x-ms-wmv",
        ".m4v": "video/x-m4v",
    }
    mime_type = mime_map.get(ext, "video/*")

    media = MediaFileUpload(str(file_path), mimetype=mime_type, chunksize=256 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print(f"Uploading: {file_path.name}  ({file_path.stat().st_size // (1024*1024)} MB)")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"\r  Progress: {pct:3}%", end="", flush=True)
    print()

    video_id = response["id"]
    privacy = body["status"]["privacyStatus"]
    scheduled = body["status"].get("publishAt")

    print(f"Upload complete!")
    print(f"  Video ID: {video_id}")
    print(f"  URL:      https://youtu.be/{video_id}")
    print(f"  Status:   {privacy}" + (f" (publishes {scheduled})" if scheduled else ""))
    print(f"\nNext steps:")
    print(f"  Set thumbnail:  python3 scripts/yt.py videos thumbnail {video_id} thumb.jpg")
    print(f"  Update metadata: python3 scripts/yt.py videos update {video_id} --title '...'")
    if privacy == "private":
        print(f"  Publish now:    python3 scripts/yt.py videos update {video_id} --privacy public")


# ── videos update ─────────────────────────────────────────────────────────────

def cmd_videos_update(args, youtube):
    resp = youtube.videos().list(part="snippet,status", id=args.video_id).execute()
    if not resp.get("items"):
        print(f"Video not found: {args.video_id}", file=sys.stderr)
        sys.exit(1)

    item = resp["items"][0]
    snippet = item["snippet"]
    status = item["status"]

    changed = False

    if args.title is not None:
        snippet["title"] = args.title
        changed = True
    if args.description is not None:
        snippet["description"] = args.description
        changed = True
    if args.tags is not None:
        snippet["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]
        changed = True
    if args.category is not None:
        snippet["categoryId"] = args.category
        changed = True
    if args.privacy is not None:
        status["privacyStatus"] = args.privacy
        changed = True
    if args.publish_at is not None:
        status["publishAt"] = args.publish_at
        status["privacyStatus"] = "private"
        changed = True

    if not changed:
        print("Nothing to update. Provide at least one field to change.")
        sys.exit(1)

    youtube.videos().update(
        part="snippet,status",
        body={"id": args.video_id, "snippet": snippet, "status": status},
    ).execute()

    print(f"Updated: https://youtu.be/{args.video_id}")
    print(f"  Title:  {snippet['title']}")
    print(f"  Status: {status['privacyStatus']}")


# ── videos delete ─────────────────────────────────────────────────────────────

def cmd_videos_delete(args, youtube):
    if not args.yes:
        confirm = input(f"Permanently delete video {args.video_id}? This cannot be undone. [y/N] ")
        if confirm.strip().lower() != "y":
            print("Aborted.")
            return
    youtube.videos().delete(id=args.video_id).execute()
    print(f"Deleted: {args.video_id}")


# ── videos thumbnail ──────────────────────────────────────────────────────────

def cmd_videos_thumbnail(args, youtube):
    from googleapiclient.http import MediaFileUpload

    img_path = Path(args.image)
    if not img_path.exists():
        print(f"Image not found: {img_path}", file=sys.stderr)
        sys.exit(1)

    ext = img_path.suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    mime = mime_map.get(ext, "image/jpeg")

    size_mb = img_path.stat().st_size / (1024 * 1024)
    if size_mb > 2:
        print(f"Warning: thumbnail is {size_mb:.1f} MB. YouTube requires ≤ 2 MB.", file=sys.stderr)

    media = MediaFileUpload(str(img_path), mimetype=mime)
    youtube.thumbnails().set(videoId=args.video_id, media_body=media).execute()
    print(f"Thumbnail set for: {args.video_id}")


# ── playlists list ─────────────────────────────────────────────────────────────

def cmd_playlists_list(args, youtube):
    items = _paginate(
        youtube.playlists().list,
        dict(part="snippet,contentDetails,status", mine=True, maxResults=50),
    )
    fmt = getattr(args, "format", "table")
    if fmt == "json":
        print(json.dumps(items, indent=2))
        return
    for pl in items:
        count = pl["contentDetails"]["itemCount"]
        status = pl["status"]["privacyStatus"]
        title = pl["snippet"]["title"][:52]
        print(f"{pl['id']}  {status:9}  {count:4} videos  {title}")


# ── playlists create ───────────────────────────────────────────────────────────

def cmd_playlists_create(args, youtube):
    resp = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": args.title,
                "description": args.description or "",
            },
            "status": {"privacyStatus": args.privacy or "public"},
        },
    ).execute()
    print(f"Created: {resp['id']}")
    print(f"URL:     https://www.youtube.com/playlist?list={resp['id']}")


# ── playlists items ────────────────────────────────────────────────────────────

def cmd_playlists_items(args, youtube):
    items = _paginate(
        youtube.playlistItems().list,
        dict(part="snippet,contentDetails", playlistId=args.playlist_id, maxResults=50),
    )
    fmt = getattr(args, "format", "table")
    if fmt == "json":
        print(json.dumps(items, indent=2))
        return
    for i, item in enumerate(items, 1):
        vid_id = item["contentDetails"]["videoId"]
        title = item["snippet"]["title"][:55]
        print(f"{i:4}.  {vid_id}  {title}")


# ── playlists add ─────────────────────────────────────────────────────────────

def cmd_playlists_add(args, youtube):
    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": args.playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": args.video_id},
            }
        },
    ).execute()
    print(f"Added {args.video_id} → {args.playlist_id}")


# ── playlists remove ───────────────────────────────────────────────────────────

def cmd_playlists_remove(args, youtube):
    resp = youtube.playlistItems().list(
        part="id",
        playlistId=args.playlist_id,
        videoId=args.video_id,
    ).execute()
    items = resp.get("items", [])
    if not items:
        print(f"Video {args.video_id} not found in playlist {args.playlist_id}", file=sys.stderr)
        sys.exit(1)
    youtube.playlistItems().delete(id=items[0]["id"]).execute()
    print(f"Removed {args.video_id} from {args.playlist_id}")


# ── playlists delete ───────────────────────────────────────────────────────────

def cmd_playlists_delete(args, youtube):
    if not args.yes:
        confirm = input(f"Delete playlist {args.playlist_id}? [y/N] ")
        if confirm.strip().lower() != "y":
            print("Aborted.")
            return
    youtube.playlists().delete(id=args.playlist_id).execute()
    print(f"Deleted playlist: {args.playlist_id}")


# ── comments list ─────────────────────────────────────────────────────────────

def cmd_comments_list(args, youtube):
    resp = youtube.commentThreads().list(
        part="snippet,replies",
        videoId=args.video_id,
        maxResults=min(args.limit or 20, 100),
        order=args.order or "relevance",
    ).execute()

    items = resp.get("items", [])
    fmt = getattr(args, "format", "table")
    if fmt == "json":
        print(json.dumps(items, indent=2))
        return

    for item in items:
        top = item["snippet"]["topLevelComment"]["snippet"]
        thread_id = item["id"]
        author = top["authorDisplayName"]
        text = top["textDisplay"].replace("\n", " ")[:120]
        likes = top["likeCount"]
        replies = item["snippet"]["totalReplyCount"]
        published = top["publishedAt"][:10]
        print(f"[{thread_id}]  {published}  {author}  ({likes} likes, {replies} replies)")
        print(f"  {text}")
        print()


# ── comments reply ────────────────────────────────────────────────────────────

def cmd_comments_reply(args, youtube):
    youtube.comments().insert(
        part="snippet",
        body={
            "snippet": {
                "parentId": args.comment_id,
                "textOriginal": args.text,
            }
        },
    ).execute()
    print("Reply posted.")


# ── search ────────────────────────────────────────────────────────────────────

def cmd_search(args, youtube):
    channel_id = _my_channel_id(youtube)
    resp = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        q=args.query,
        type=args.type or "video",
        maxResults=min(args.limit or 10, 50),
        order="relevance",
    ).execute()

    items = resp.get("items", [])
    fmt = getattr(args, "format", "table")
    if fmt == "json":
        print(json.dumps(items, indent=2))
        return

    for item in items:
        kind = item["id"].get("kind", "")
        if "video" in kind:
            rid = item["id"].get("videoId", "?")
            url = f"https://youtu.be/{rid}"
        elif "playlist" in kind:
            rid = item["id"].get("playlistId", "?")
            url = f"https://youtube.com/playlist?list={rid}"
        else:
            rid = item["id"].get("channelId", "?")
            url = f"https://youtube.com/channel/{rid}"
        title = item["snippet"]["title"][:55]
        published = item["snippet"]["publishedAt"][:10]
        print(f"{rid}  {published}  {title}")
        _ = url  # available in JSON output


# ── export ────────────────────────────────────────────────────────────────────

def cmd_export(args, youtube):
    """Export every channel video to CSV or JSON (stdout)."""
    uploads_id = _uploads_playlist_id(youtube)

    items = _paginate(
        youtube.playlistItems().list,
        dict(part="contentDetails", playlistId=uploads_id, maxResults=50),
    )
    video_ids = [v["contentDetails"]["videoId"] for v in items]
    details = _fetch_video_details(youtube, video_ids)

    rows = []
    for vid_id in video_ids:
        d = details.get(vid_id)
        if not d:
            continue
        s = d["snippet"]
        rows.append({
            "id": vid_id,
            "title": s.get("title", ""),
            "description": s.get("description", ""),
            "tags": "|".join(s.get("tags", [])),
            "category_id": s.get("categoryId", ""),
            "published_at": s.get("publishedAt", ""),
            "status": d["status"].get("privacyStatus", ""),
            "duration": d.get("contentDetails", {}).get("duration", ""),
            "views": d.get("statistics", {}).get("viewCount", ""),
            "likes": d.get("statistics", {}).get("likeCount", ""),
            "comments": d.get("statistics", {}).get("commentCount", ""),
            "url": f"https://youtu.be/{vid_id}",
        })

    fmt = getattr(args, "format", "csv")
    if fmt == "json":
        print(json.dumps(rows, indent=2))
    else:
        if rows:
            writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


# ── bulk-update ───────────────────────────────────────────────────────────────

def cmd_bulk_update(args, youtube):
    """Update multiple videos from a CSV file.

    Required column: id
    Optional columns: title, description, tags (pipe-separated), category_id, status
    Empty cells are skipped; the existing value is preserved.
    """
    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("CSV is empty.")
        return

    if "id" not in rows[0]:
        print("CSV must have an 'id' column.", file=sys.stderr)
        sys.exit(1)

    ids = [r["id"].strip() for r in rows if r.get("id", "").strip()]
    print(f"Fetching current metadata for {len(ids)} videos...")

    current = _fetch_video_details(youtube, ids, part="snippet,status")

    updated = 0
    skipped = 0
    for row in rows:
        vid_id = row.get("id", "").strip()
        if not vid_id or vid_id not in current:
            print(f"  Skip (not found): {vid_id}")
            skipped += 1
            continue

        item = current[vid_id]
        snippet = item["snippet"]
        status = item["status"]
        changed = False

        if row.get("title", "").strip():
            snippet["title"] = row["title"].strip()
            changed = True
        if "description" in row:
            snippet["description"] = row["description"]
            changed = True
        if row.get("tags", "").strip():
            snippet["tags"] = [t.strip() for t in row["tags"].split("|") if t.strip()]
            changed = True
        if row.get("category_id", "").strip():
            snippet["categoryId"] = row["category_id"].strip()
            changed = True
        if row.get("status", "").strip():
            status["privacyStatus"] = row["status"].strip()
            changed = True

        if not changed:
            skipped += 1
            continue

        youtube.videos().update(
            part="snippet,status",
            body={"id": vid_id, "snippet": snippet, "status": status},
        ).execute()

        print(f"  Updated: {vid_id}  {snippet['title'][:55]}")
        updated += 1
        time.sleep(0.15)  # stay well within quota

    print(f"\nDone. Updated {updated} videos, skipped {skipped}.")


# ── Argument parser ────────────────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        prog="yt.py",
        description="YouTube Creator CLI — manage your channel with the YouTube Data API v3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # auth
    p = sub.add_parser("auth", help="Set up or refresh OAuth2 credentials")
    p.set_defaults(func=cmd_auth)

    # whoami
    p = sub.add_parser("whoami", help="Show authenticated channel info")
    p.set_defaults(func=cmd_whoami)

    # ── videos ────────────────────────────────────────────────────────────────
    p_vid = sub.add_parser("videos", help="Video operations")
    vs = p_vid.add_subparsers(dest="subcommand", metavar="SUBCOMMAND")
    vs.required = True

    # videos list
    p = vs.add_parser("list", help="List channel videos")
    p.add_argument("--limit", "-n", type=int, default=50, metavar="N", help="Max results (default 50)")
    p.add_argument("--status", choices=["public", "private", "unlisted"], help="Filter by privacy status")
    p.add_argument("--format", choices=["table", "csv", "json"], default="table")
    p.set_defaults(func=cmd_videos_list)

    # videos get
    p = vs.add_parser("get", help="Get full details for a video")
    p.add_argument("video_id", help="YouTube video ID (e.g. dQw4w9WgXcQ)")
    p.add_argument("--format", choices=["table", "json"], default="table")
    p.set_defaults(func=cmd_videos_get)

    # videos upload
    p = vs.add_parser("upload", help="Upload a video file")
    p.add_argument("file", help="Path to the video file")
    p.add_argument("--title", "-t", help="Video title (defaults to filename)")
    p.add_argument("--description", "-d", default="", help="Video description")
    p.add_argument("--tags", help="Comma-separated tags")
    p.add_argument("--category", default="22", metavar="ID", help="Category ID (default 22 = People & Blogs)")
    p.add_argument("--privacy", choices=["public", "private", "unlisted"], default="private",
                   help="Privacy status (default: private)")
    p.add_argument("--schedule", metavar="ISO8601",
                   help="Schedule publish at this UTC datetime, e.g. 2025-12-31T18:00:00Z")
    p.set_defaults(func=cmd_videos_upload)

    # videos update
    p = vs.add_parser("update", help="Update video metadata")
    p.add_argument("video_id", help="YouTube video ID")
    p.add_argument("--title", "-t", help="New title")
    p.add_argument("--description", "-d", help="New description (use '' to clear)")
    p.add_argument("--tags", help="Comma-separated tags (replaces all existing tags)")
    p.add_argument("--category", metavar="ID", help="Category ID")
    p.add_argument("--privacy", choices=["public", "private", "unlisted"], help="Privacy status")
    p.add_argument("--publish-at", dest="publish_at", metavar="ISO8601",
                   help="Schedule publish datetime (UTC); sets status to private until then")
    p.set_defaults(func=cmd_videos_update)

    # videos delete
    p = vs.add_parser("delete", help="Permanently delete a video")
    p.add_argument("video_id", help="YouTube video ID")
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    p.set_defaults(func=cmd_videos_delete)

    # videos thumbnail
    p = vs.add_parser("thumbnail", help="Set a custom thumbnail for a video")
    p.add_argument("video_id", help="YouTube video ID")
    p.add_argument("image", help="Path to thumbnail image (JPG or PNG, max 2 MB, 1280×720 recommended)")
    p.set_defaults(func=cmd_videos_thumbnail)

    # ── playlists ─────────────────────────────────────────────────────────────
    p_pl = sub.add_parser("playlists", help="Playlist operations")
    ps = p_pl.add_subparsers(dest="subcommand", metavar="SUBCOMMAND")
    ps.required = True

    # playlists list
    p = ps.add_parser("list", help="List all channel playlists")
    p.add_argument("--format", choices=["table", "json"], default="table")
    p.set_defaults(func=cmd_playlists_list)

    # playlists create
    p = ps.add_parser("create", help="Create a new playlist")
    p.add_argument("title", help="Playlist title")
    p.add_argument("--description", "-d", default="", help="Playlist description")
    p.add_argument("--privacy", choices=["public", "private", "unlisted"], default="public")
    p.set_defaults(func=cmd_playlists_create)

    # playlists items
    p = ps.add_parser("items", help="List videos in a playlist")
    p.add_argument("playlist_id", help="Playlist ID")
    p.add_argument("--format", choices=["table", "json"], default="table")
    p.set_defaults(func=cmd_playlists_items)

    # playlists add
    p = ps.add_parser("add", help="Add a video to a playlist")
    p.add_argument("playlist_id", help="Playlist ID")
    p.add_argument("video_id", help="Video ID to add")
    p.set_defaults(func=cmd_playlists_add)

    # playlists remove
    p = ps.add_parser("remove", help="Remove a video from a playlist")
    p.add_argument("playlist_id", help="Playlist ID")
    p.add_argument("video_id", help="Video ID to remove")
    p.set_defaults(func=cmd_playlists_remove)

    # playlists delete
    p = ps.add_parser("delete", help="Delete a playlist (videos are not deleted)")
    p.add_argument("playlist_id", help="Playlist ID")
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    p.set_defaults(func=cmd_playlists_delete)

    # ── comments ──────────────────────────────────────────────────────────────
    p_cm = sub.add_parser("comments", help="Comment operations")
    cms = p_cm.add_subparsers(dest="subcommand", metavar="SUBCOMMAND")
    cms.required = True

    # comments list
    p = cms.add_parser("list", help="List top-level comments on a video")
    p.add_argument("video_id", help="Video ID")
    p.add_argument("--limit", "-n", type=int, default=20, metavar="N")
    p.add_argument("--order", choices=["relevance", "time"], default="relevance")
    p.add_argument("--format", choices=["table", "json"], default="table")
    p.set_defaults(func=cmd_comments_list)

    # comments reply
    p = cms.add_parser("reply", help="Reply to a comment thread")
    p.add_argument("comment_id", help="Comment thread ID (from 'comments list' output)")
    p.add_argument("text", help="Reply text")
    p.set_defaults(func=cmd_comments_reply)

    # ── search ────────────────────────────────────────────────────────────────
    p = sub.add_parser("search", help="Search your channel content")
    p.add_argument("query", help="Search query")
    p.add_argument("--limit", "-n", type=int, default=10, metavar="N")
    p.add_argument("--type", choices=["video", "playlist", "channel"], default="video")
    p.add_argument("--format", choices=["table", "json"], default="table")
    p.set_defaults(func=cmd_search)

    # ── export ────────────────────────────────────────────────────────────────
    p = sub.add_parser("export", help="Export all channel videos to CSV or JSON (stdout)")
    p.add_argument("--format", choices=["csv", "json"], default="csv")
    p.set_defaults(func=cmd_export)

    # ── bulk-update ───────────────────────────────────────────────────────────
    p = sub.add_parser("bulk-update", help="Bulk-update video metadata from a CSV file")
    p.add_argument(
        "csv_file",
        help="CSV with columns: id (required), title, description, tags (pipe-separated), category_id, status",
    )
    p.set_defaults(func=cmd_bulk_update)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        youtube = get_service()
        args.func(args, youtube)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        # Surface API errors clearly
        try:
            from googleapiclient.errors import HttpError
            if isinstance(e, HttpError):
                try:
                    detail = json.loads(e.content.decode())
                    msg = detail.get("error", {}).get("message", str(e))
                    code = detail.get("error", {}).get("code", e.resp.status)
                    print(f"YouTube API error {code}: {msg}", file=sys.stderr)
                except Exception:
                    print(f"YouTube API error: {e}", file=sys.stderr)
                sys.exit(1)
        except ImportError:
            pass
        raise


if __name__ == "__main__":
    main()
