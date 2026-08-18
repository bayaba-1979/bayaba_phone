# Mobile-First Multi-Platform Content Foundry — Boilerplate

![One phone, the whole studio — a content foundry running on a single Galaxy S21](assets/social-preview.jpg)

> **One Galaxy S21. ~$20/month. A one-person media studio — and a 24/7 care system.**
> Powered by Termux/PRoot & MCP. Every step hard-verified by `returncode == 0` — no agent hallucinations.
> **548 commits · 905 files · 129 notebooks · 8 shipped systems · 3 weeks.**
> Zero PC · resilience-first · multi-channel (Git SSOT → PWA / Tistory / YouTube / Telegram).
>
> **Made in Korea — not a developer.** I don't sit easy at a keyboard; I can't stand that kind of building. Fourteen-hour days of physical labor, and in the cracks of it, all of this — spoken into a terminal, not typed. The nobles take a walk to rest. I rest by working.
>
> **The build is done. Now I open it and teach.** Fork it, cite it, run it on the phone in your pocket.

![hardware](https://img.shields.io/badge/hardware-1%C3%97%20Galaxy%20S21-9cf) ![cost](https://img.shields.io/badge/cost-~%2420%2Fmonth-success) ![commits](https://img.shields.io/badge/commits-548-blue) ![systems](https://img.shields.io/badge/systems-8%20shipped-brightgreen) ![license](https://img.shields.io/badge/license-MIT-lightgrey)

## The origin — proof, not a poster

![The real worksite — grease-stained pots, soiled gloves, a knife and a torch, and in the middle, a phone with a terminal open](assets/origin-worksite.jpg)

This image is not generated. It's the worksite where this was built.

Anyone can commission a poster or apply a filter. Nobody can fake the grease on the pots, the dirt worked into the gloves, a knife with residue, a butane torch — the real cutting board of a worker. And in the middle of it, a Galaxy S21, charging cable in, a terminal open, mid-conversation with an agent.

That's the whole life in one frame: fourteen-hour days, and the building happens in the cracks. The nobles take a walk to rest. I rest by working.

---

## What is this?

One phone does two jobs.

By **day**, it's a **guardian angel** — a care daemon watching over my sister 24/7.
By **night**, it's a **dream factory** — a publishing pipeline that turns a single phone into a media company.

Three weeks of building (2026-07-23 → 08-16). No new features. What's left is **opening it and teaching you to run it** — because everything here is reproducible. Copy it to your phone and run the same thing.

**~$20 a month.** Claude Code + DeepSeek + Aider. Cheaper than a Netflix subscription. If this runs on hardware you'd recycle, so can yours — *that's* the flex.

## The architecture

```
┌─────────────────────────────────────────────────────┐
│         Words only · One phone · For my sister       │
│                                                     │
│  📱 Galaxy S21  →  the secret room (Termux + proot) │
│                          │                          │
│         ┌────────────────┼──────────────────┐       │
│         │                │                  │       │
│    Writer bot        Design/PD bot       Fixer bot  │
│  (Claude Code)     (Grok · two lanes)     (Aider)  │
│  publish·translate  layout·docu          patch·build│
│         │                │                  │       │
│         └────────────────┼──────────────────┘       │
│                    ┌─────┴──────────┐               │
│                    │  7 workshops    │               │
│                    │ GitHub (5 repos)│               │
│                    │ Pages           │               │
│                    │ YouTube         │               │
│                    │ Naver · Tistory │               │
│                    │ Telegram        │               │
│                    └────────────────┘               │
│                                                     │
│  548 commits · 905 files · 129 notebooks · 8 systems│
│  Build is done → now I open it and teach            │
└─────────────────────────────────────────────────────┘
```

## By the numbers

| Metric | Value |
|--------|-------|
| Build time | 3 weeks (2026-07-23 → 08-16) |
| Commits | 548 |
| Files | 905 |
| Notebooks | 129 |
| Shipped systems | 8 (webzine · care daemon · textbook · publishing · video · …) |
| AI agents | 3 (writer · designer/PD · patcher) |
| Repos | 5, all public |
| Monthly cost | ~$20 (one Netflix subscription) |
| Hardware | 1 old Galaxy S21 (PRoot as a PC) |

## The roadmap — seed → spread → sublimate

The direction isn't technical. It's human — the lowest hardware, the warmest purpose, the widest reach.

**Act I · Seed (done).** One Galaxy S21 on Termux/PRoot. A care daemon for my sister + a mobile content foundry — running today.

**Act II · Spread (next).** Global open source — forks, issues, citations from Reddit · GitHub · Hacker News. Then public-good proof: national / public R&D validation, so "it works" is a verified fact, not a claim.

**Act III · Sublimate (north star).** *AI for the marginalized* — care technology that lifts up the overlooked, on hardware anyone can afford. Measured not by specs, but by **who it saves**.

## Quick links

| Looking for | Link |
|-------------|------|
| **Full portal** | [index.html](.) |
| **Constitution** | [CONSTITUTION.md](CONSTITUTION.md) |
| **Working rules** | [CLAUDE.md](CLAUDE.md) |
| **Turning point (build stops)** | [_notebook/98-turning-point-2026-08-16_Claude.md](_notebook/98-turning-point-2026-08-16_Claude.md) |
| **Showcase (8 systems)** | [_notebook/97-s21-solutions-showcase_Claude.md](_notebook/97-s21-solutions-showcase_Claude.md) |
| **Dev log** | [_notebook/99-devlog.md](_notebook/99-devlog.md) |
| **Notebook index** | [_notebook/00-INDEX.md](_notebook/00-INDEX.md) |
| **Textbook** | [_textbook/index.md](_textbook/index.md) |
| **🚀 10-minute start** | [navigator.sh](navigator.sh) |
| **Spawn engine (satellites)** | [g/spawn.sh](g/spawn.sh) |
| **One-line install** | [g/install.sh](g/install.sh) |
| **Care daemon (guardian)** | [care/care-daemon.sh](care/care-daemon.sh) |

## 🚀 10-minute start — copy → configure → run

This repo is a **boilerplate**. Click **"Use this template"**, fill in your name / blog / channel, and it runs as-is. The existing content (piano · care · faith) ships as a **worked example** — swap the variable points for your own.

| Min | Step | Command | Result |
|-----|------|---------|--------|
| 0 | Copy | GitHub → **Use this template** | `helena_phone` under your account |
| 2 | Configure | `bash navigator.sh` | `ecosystem.json` + `.secrets.env` |
| 5 | Spawn | `bash g/spawn.sh` | 4 satellite repos + secret wiring |
| 8 | Run | `bash g/install.sh` | Termux/proot/Claude workspace |
| 10 | Verify | Pages + workflows | Tistory / YouTube pipeline live |

### 0 min — Copy (Use this template)

- Repo page → **"Use this template"** → "Create a new repository"
- Name it anything (default `helena_phone`), keep it **Public** (public is the philosophy)
- Or CLI: `gh repo create <you>/helena_phone --template helena751107/helena_phone --public`

### 2 min — Navigator (setup wizard)

```bash
cd helena_phone
bash navigator.sh
```

Three things it asks:
1. **GitHub username** (ownership)
2. **Blogs / channels** — 5 Tistory slugs, 2 YouTube handles (or keep the samples)
3. **Secrets** — step-by-step for BotFather (TG), Google Cloud Console (YouTube), Discord

→ Produces `configs/ecosystem.json` (mapping) + `.secrets.env` (secrets). **Both gitignored** — never pushed.

> **🔐 The secret model — "env var on the phone = source of truth"**
> Every secret lives in `.secrets.env` inside your proot Ubuntu — that's the SSOT. `g/install.sh` `source`s it into `~/.bashrc`, so `TG_TOKEN` · `TISTORY_EMAIL` · `YOUTUBE_*` are env vars in every new shell. On GitHub, `g/spawn.sh` wires **only `TG_TOKEN`/`TG_CHAT`** via `gh secret set` (the only secrets the workflow actually reads). Everything else (Tistory/YT/Discord/Tailscale) stays local — read by on-phone scripts, never pushed.

### 5 min — Spawn (satellite repos)

```bash
bash g/spawn.sh            # run
bash g/spawn.sh --dry-run  # preview first
```

Reads `ecosystem.json`, creates the 4 satellites (piano / metalcare / faith / log) from the template, and wires TG secrets into each. (Needs `gh CLI` + `gh auth login`.)

### 8 min — Run (workspace)

```bash
bash g/install.sh          # on your phone (Termux/proot)
```

### 10 min — Verify

- Pages: `https://<you>.github.io/helena_phone/`
- Workflows: each repo's **Actions** tab → run `tistory-sync` once → RSS lands in `기자/`

> **Why so light?** Drift sync is handled by a central reusable workflow (`uses: helena751107/helena_phone/.github/workflows/tistory-sync.yml@main`). Fix the logic once, every fork gets it automatically.

## 📐 The production recipe — 3 scripts + 3-layer verification

Once the skeleton stands, production runs on a **recipe**. One raw asset (`_notebook/*.md`) → a PWA + Tistory pair, on a standard process.

| Script | Role |
|--------|------|
| `bash scripts/preflight.sh` | **Table-setter** — checks consumable assets (Tistory session · YouTube OAuth · GitHub · Telegram) before a batch. On FAIL, renew first. |
| `python3 tistory-naver/renew_sessions.py --if-needed` | **Self-healing sessions** — re-logs into the 5 Tistory blogs only on expiry. Called automatically before publishing — no one babysits sessions. |
| `bash scripts/quota.sh` | **Today's quota** — Tistory 15/day (account) · YouTube 1600 units · Threads 500 chars / 250/day. SSOT = `configs/quota-manifest.json`. |
| `bash scripts/make_pair.sh` | **Pair publish** — preflight → PWA build (gap=0 gate) → Tistory (director gate → batch). Single entry point. |

**Three-layer verification (catch failures early):**
1. **Table-setter (preflight)** — session/token expiry filtered out before the batch.
2. **Exit-code gate** — "done" is judged by `returncode` and file existence, not by an agent's word.
3. **gap_count = 0** — a missing PWA page blocks deployment.

> **🥛 Tistory sessions last about 24 hours.** Reboot or expiry — it doesn't matter; the recipe checks and re-logs in automatically before every publish (`make_pair`). "Stay signed in" isn't available (verified), but self-healing swaps in a fresh session for you.
>
> **One prerequisite** — `tistory-naver/accounts.json` (Kakao email + password). Copy `accounts.json.template`, fill in yours, and both self-healing and publishing work. (Gitignored — never pushed.)

**Bait-channel personas** — the same material, re-voiced per audience: Naver = older generation, Threads = MZ generation (`configs/bait-voice.json`).

> **Scope:** this recipe is for content (one-person media). The care mesh (Tailscale) and care daemon are a separate track — not mixed in here.

## 📱 One-line install (existing workspace)

```bash
curl -sL https://raw.github.com/helena751107/helena_phone/main/g/install.sh | bash
```

> 🇰🇷 Korean guide (한국어 안내) → [index.html](.)
