---
name: nanobanana
description: Generate and edit raster images using Nano Banana (the Gemini CLI nanobanana extension). Use this skill whenever the user wants to create, generate, make, draw, design, restore, or edit an actual image/visual asset — blog featured images, YouTube thumbnails, banners, app icons, favicons, rendered diagrams/flowchart images, seamless patterns/textures, illustrations, photos, comic/story panels, or any picture or artwork. Do NOT use it for code-based or editable diagrams (Mermaid, ASCII, SVG/markup), or for data-driven charts plotted from a dataset — those need a different tool.
user-invocable: true
allowed-tools: Bash(gemini:*)
---

# Nano Banana Image Generation

Generate images via the Gemini CLI's `nanobanana` extension. Claude has no native
image-rendering ability, so this CLI is the only way to actually produce an image file —
don't fall back to describing an image in prose when the user wants a real asset.

## When to Use This Skill

Use it whenever the user wants an actual rendered image: an illustration, thumbnail,
featured image, banner, icon, favicon, rendered diagram, pattern/texture, restored photo,
or story/comic panels. Trigger on verbs like generate, create, make, draw, design,
visualize, restore, or edit *when the target is an image*.

Skip it when the user wants something that only looks adjacent:
- Code/markup diagrams (Mermaid, Graphviz, ASCII art, hand-written SVG) — those are text.
- Charts/graphs plotted from a dataset (use a plotting library, not image generation).
- UI components or design *systems* in code.

## Before First Use

1. Confirm the extension is installed:
   ```bash
   gemini extensions list | grep nanobanana
   ```
2. If missing, install it:
   ```bash
   gemini extensions install https://github.com/gemini-cli-extensions/nanobanana
   ```
3. API key: the extension stores its key either in the `GEMINI_API_KEY` env var **or**
   in the OS keychain (configured via the extension settings). Don't gate on
   `$GEMINI_API_KEY` being set — a keychain-stored key won't show up there but still works.
   Only act if a real run fails with an auth error, in which case set the key:
   ```bash
   export GEMINI_API_KEY="your-key"
   ```

## The `--yolo` flag

Always pass `--yolo`. The nanobanana commands call MCP tools that otherwise pause for an
interactive approval prompt; since this skill runs non-interactively, that prompt would
hang the run. `--yolo` auto-approves the tool calls so generation completes unattended.

## Command Selection

| User Request | Command |
|--------------|---------|
| "make me a blog header" | `/generate` |
| "create an app icon" | `/icon` |
| "draw a flowchart image of..." | `/diagram` |
| "fix this old photo" | `/restore` |
| "remove the background / edit this image" | `/edit` |
| "create a repeating texture" | `/pattern` |
| "make a comic strip" | `/story` |
| anything else, natural language | `/nanobanana` |

## Commands and their real options

These option lists are validated by the extension's command parser — passing an option or
value outside the allowed set makes the command return an error instead of an image, so
stick to exactly what's listed here.

These values are pinned to nanobanana v1.0.12. If a command returns an "Invalid option(s)"
error for something documented here, the extension has likely been updated and its option
set has drifted — trust the command's own error output (or `gemini "/<command> --help"`)
over this table, and adjust the call accordingly.

### `/generate` — text-to-image
```bash
gemini --yolo "/generate 'prompt'"
```
- `--count=N` — N variations, 1-8 (default 1)
- `--styles="..."` — comma-separated, from: `photorealistic, watercolor, oil-painting, sketch, pixel-art, anime, vintage, modern, abstract, minimalist`
- `--variations="..."` — comma-separated, from: `lighting, angle, color-palette, composition, mood, season, time-of-day`
- `--format=grid|separate` (default `separate`)
- `--seed=123`
- `--preview`

There is **no** `--aspect` or `--size` option for `/generate`. To influence aspect ratio or
framing, describe it in the prompt itself (e.g. "wide 16:9 banner composition",
"square thumbnail", "tall vertical 9:16 poster").

### `/icon` — app icons, favicons, UI elements
```bash
gemini --yolo "/icon 'minimalist productivity app logo' --sizes='64,128,256,512' --type='app-icon' --corners='rounded'"
```
- `--sizes="..."` — from: `16, 32, 64, 128, 256, 512, 1024`
- `--type="app-icon|favicon|ui-element"` (default `app-icon`)
- `--style="flat|skeuomorphic|minimal|modern"` (default `modern`)
- `--format="png|jpeg"` (default `png`)
- `--background="transparent|white|black"` or a color name (default `transparent`)
- `--corners="rounded|sharp"` (default `rounded`)
- `--preview`

### `/diagram` — rendered technical diagrams
```bash
gemini --yolo "/diagram 'user authentication flow with OAuth' --type='flowchart' --style='professional'"
```
- `--type="flowchart|architecture|network|database|wireframe|mindmap|sequence"` (default `flowchart`)
- `--style="professional|clean|hand-drawn|technical"` (default `professional`)
- `--layout="horizontal|vertical|hierarchical|circular"` (default `hierarchical`)
- `--complexity="simple|detailed|comprehensive"` (default `detailed`)
- `--colors="mono|accent|categorical"` (default `accent`)
- `--annotations="minimal|detailed"` (default `detailed`)
- `--preview`

(Note: `--style` here does **not** accept `modern` — that's an `/icon` value.)

### `/pattern` — seamless textures and patterns
```bash
gemini --yolo "/pattern 'subtle geometric tech background' --size='512x512' --type='seamless'"
```
- `--size="WxH"` (e.g. `128x128`, `256x256`, `512x512`; default `256x256`)
- `--type="seamless|texture|wallpaper"` (default `seamless`)
- `--style="geometric|organic|abstract|floral|tech"` (default `abstract`)
- `--density="sparse|medium|dense"` (default `medium`)
- `--colors="mono|duotone|colorful"` (default `colorful`)
- `--repeat="tile|mirror"` (default `tile`)
- `--preview`

### `/story` — sequential / narrative panels
```bash
gemini --yolo "/story 'a seed growing into a tree' --steps=4 --layout='comic'"
```
- `--steps=N` — 2-8 (default 4)
- `--type="story|process|tutorial|timeline"` (default `story`)
- `--style="consistent|evolving"` (default `consistent`)
- `--layout="separate|grid|comic"` (default `separate`)
- `--transition="smooth|dramatic|fade"` (default `smooth`)
- `--format="storyboard|individual"` (default `individual`)
- `--preview`

### `/edit` and `/restore` — modify an existing image
```bash
gemini --yolo "/edit file.png 'remove the background'"
gemini --yolo "/restore old_photo.jpg 'fix scratches and restore color'"
```
Both take a filename, then an instruction in quotes, then optionally `--preview`. They
accept no other options.

## Sizing / aspect ratio

Only some commands take explicit dimensions:
- `/icon` → `--sizes`
- `/pattern` → `--size=WxH`

`/generate`, `/diagram`, and `/story` have no dimension flag — convey the desired
shape/ratio in the prompt text instead (e.g. "wide 16:9 banner", "square 1:1",
"vertical 9:16 story format", "1200x630 social-preview composition").

## Model Selection

Default model: `gemini-3.1-flash-image-preview`.

To switch models, set `NANOBANANA_MODEL`:
```bash
# Higher quality / better reasoning (Nano Banana Pro)
export NANOBANANA_MODEL=gemini-3-pro-image-preview
# Older v1 flash model
export NANOBANANA_MODEL=gemini-2.5-flash-image
```

## Output Location

Generated images are saved to `./nanobanana-output/` (created automatically) relative to
the current working directory. After a run, list that directory, report the **absolute**
path of the new file(s) to the user, and present the most recent one.

## Examples

```bash
# Blog featured image — modern illustration
gemini --yolo "/generate 'modern flat illustration of a developer coding at a laptop, purple and blue gradient background, minimalist, wide 16:9 banner composition, no text' --preview"

# Three editorial-photo variations
gemini --yolo "/generate 'editorial photo of a coffee cup beside a laptop on a wooden desk, morning sunlight, shallow depth of field, no text' --count=3 --styles='photorealistic'"

# App icon set
gemini --yolo "/icon 'minimalist app logo for a productivity tool' --sizes='64,128,256,512' --type='app-icon' --corners='rounded'"

# Auth flow diagram
gemini --yolo "/diagram 'user authentication flow with OAuth' --type='flowchart' --style='professional'"
```

## Refinements and Iterations

- "Try again" / "give me options" → regenerate with `--count=3`.
- "Make it more [adjective]" → adjust the prompt text and regenerate.
- "Edit this one" → `gemini --yolo "/edit nanobanana-output/<file>.png 'adjustment'"`.
- "Different style" → set `--styles="..."` from the allowed list for that command.

## Prompt Tips

1. Be specific about style, mood, colors, and composition.
2. Add "no text" when you don't want rendered words in the image.
3. Reference concrete styles ("editorial photography", "flat illustration", "3D render", "watercolor").
4. State the intended shape/ratio in words, since `/generate` has no aspect flag.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Auth / API key error at runtime | Key may be unset; `export GEMINI_API_KEY="your-key"` or reconfigure the extension's keychain entry |
| Extension not found | Run the install command from "Before First Use" |
| "Invalid option(s)" error | You passed a flag/value outside the allowed set — check the command's option list above. If the value *is* listed, the extension may have updated past v1.0.12; run `gemini "/<command> --help"` and follow its current option set |
| Quota exceeded | Wait for reset, or switch to a flash model via `NANOBANANA_MODEL` |
| Generation failed | Simplify the prompt; check it for policy violations |
| Output directory missing | Created automatically on first successful run |
