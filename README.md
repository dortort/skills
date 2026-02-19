# Skills

A collection of [Agent Skills](https://agentskills.io) -- reusable instruction packages that teach AI coding agents how to perform specialized tasks. Skills follow the open [Agent Skills specification](https://agentskills.io/specification) and work across multiple AI tools.

## Available Skills

| Skill | Description |
|-------|-------------|
| [nlm-new-topic](skills/nlm-new-topic/SKILL.md) | Creates a complete NotebookLM learning package for a topic -- research, summaries, slide decks, videos, audio, and per-unit infographics |
| [nlm-deepdive](skills/nlm-deepdive/SKILL.md) | Deep dives into a subtopic within an existing NotebookLM notebook with parallel artifact generation |

## Installation

### Claude Code Plugin (recommended)

Install all skills at once as a [Claude Code plugin](https://code.claude.com/docs/en/plugins):

```bash
claude plugin add -- https://github.com/dortort/skills
```

After installation the skills are available as slash commands with the `dortort` namespace:

- `/dortort:nlm-new-topic`
- `/dortort:nlm-deepdive`

To remove the plugin:

```bash
claude plugin remove dortort
```

### Manual (copy individual skills)

Each skill is a directory containing a `SKILL.md` file. Copy the skill folder into the appropriate location for your agent:

| Agent | Personal | Project-local | Docs |
|-------|----------|---------------|------|
| [Claude Code](https://code.claude.com/docs/en/skills) | `~/.claude/skills/` | `.claude/skills/` | [Skills docs](https://code.claude.com/docs/en/skills) |
| [OpenAI Codex](https://developers.openai.com/codex/skills/) | `~/.agents/skills/` | `.agents/skills/` | [Skills docs](https://developers.openai.com/codex/skills/) |
| [Cursor](https://cursor.com) | -- | `.cursor/skills/` | -- |
| [OpenCode](https://opencode.ai/docs/skills/) | `~/.config/opencode/skills/` | `.opencode/skills/` | [Skills docs](https://opencode.ai/docs/skills/) |

Example:

```bash
# Install a skill for Claude Code (personal, all projects)
cp -r skills/nlm-new-topic ~/.claude/skills/nlm-new-topic

# Or project-local
cp -r skills/nlm-new-topic .claude/skills/nlm-new-topic
```

OpenCode also auto-discovers skills in `.claude/skills/` and `.agents/skills/`.

Any agent that supports the [Agent Skills](https://agentskills.io) standard can use these skills. See [Integrate skills](https://agentskills.io/integrate-skills) for other agents.

## Skill Format

Each skill follows the [Agent Skills specification](https://agentskills.io/specification):

```
skill-name/
└── SKILL.md          # Required: YAML frontmatter + markdown instructions
```

The `SKILL.md` file contains:

```yaml
---
name: skill-name
description: What the skill does and when to use it
user-invocable: true
---

# Skill instructions in markdown
```

## Skill Authoring Resources

Best practices for writing effective skills:

- [The Complete Guide to Building Skills for Claude](https://claude.com/blog/complete-guide-to-building-skills-for-claude) (Anthropic) -- 32-page guide covering planning, writing, testing, and distributing skills ([PDF](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf))
- [Agent Skills](https://developers.openai.com/codex/skills/) (OpenAI) -- Codex skills documentation with authoring best practices and evaluation guidance
- [Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills/) (OpenAI) -- how to measure skill effectiveness and iterate
- [Shell + Skills + Compaction: Tips for long-running agents](https://developers.openai.com/blog/skills-shell-tips/) (OpenAI) -- practical patterns for skills that run complex workflows
- [What are skills?](https://agentskills.io/what-are-skills) (Agent Skills) -- overview of the open standard
- [Agent Skills Specification](https://agentskills.io/specification) (Agent Skills) -- full format spec for SKILL.md files

## Other Skill Repositories

- [anthropics/skills](https://github.com/anthropics/skills) -- Anthropic's official skill collection
- [openai/skills](https://github.com/openai/skills) -- OpenAI's official skill collection
- [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) -- Marketing-focused skills
- [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) -- Andrej Karpathy-inspired skills

## Contributing

To add a new skill:

1. Create a new directory under `skills/` matching the skill name
2. Add a `SKILL.md` with valid YAML frontmatter (`name` and `description` are required)
3. Follow the [specification](https://agentskills.io/specification) for naming conventions and format
4. Submit a pull request
