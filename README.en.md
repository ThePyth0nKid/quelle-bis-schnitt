# quelle-bis-schnitt

A marketplace of Claude Code plugins. It maps a workflow that starts with a question and ends with a finished video:

**Research → Evidence → Script → Shoot → Edit → Delivery**

Guiding rule: **agents research, rules advise, a human decides and signs off.**

[Deutsche Fassung](README.md)

The skills, tools and docs are written in German. Claude reads and applies them in any language, so you can work in English.

## What is inside

| Plugin | Purpose | Contents |
|---|---|---|
| `recherche` | find sources, collect evidence, check quotes | skills `quellen-zugang` (source access), `belegregeln` (evidence rules), `recherche-runde` (research round); agent `faktenpruefer` (fact checker); tool `zitate_pruefen.py` (quote checker); Exa MCP |
| `jina-lesen` | read web pages and PDFs as text | Jina MCP with your own key |
| `tavily-suche` | a second search engine next to Exa | Tavily MCP with your own key |
| `skript` | spoken scripts for long and short videos | skills `skript`, `skript-lang`, `skript-short`, `skript-snack`, `skript-trailer`, `hook`, `sprechtext`, `anti-slop-writing`, `viral-methode`; agents `hook-blind`, `skript-kritiker`; check scripts |
| `studio` | two-camera shoot, teleprompter, audio, edit in DaVinci Resolve, delivery | skills `dreh-setup`, `zwei-kamera`, `prompter`, `ton-mastering`, `resolve-schnitt`, `abgabe`; command `/studio:einrichten`; tool `studio` |
| `arbeitsweise` | rules for working with agents | skills `arbeitsweise`, `deploy-lock`; tool `deploy_waechter` |
| `akte` | evidence board with mandatory sources, as an MCP | **coming** from the `die-akte` repo |

## Install

In Claude Code:

```text
/plugin marketplace add ThePyth0nKid/quelle-bis-schnitt
/plugin install recherche@quelle-bis-schnitt
/plugin install skript@quelle-bis-schnitt
/plugin install studio@quelle-bis-schnitt
/plugin install arbeitsweise@quelle-bis-schnitt
```

Every plugin installs on its own. Take only what you need.

**Jina and Tavily** need your own key from the provider. Claude Code asks for it when you install through `/plugin` and keeps
it as a sensitive value in your system's secure storage, not in `settings.json`. To change it later, run
`/plugin configure jina-lesen@quelle-bis-schnitt`.

**The `studio` tool** (click check, mastering, camera pairs, teleprompter, transcript) is a Python package:

```text
uv tool install "git+https://github.com/ThePyth0nKid/quelle-bis-schnitt#subdirectory=plugins/studio/werkzeuge"
studio --version
```

Then run `/studio:einrichten` in Claude Code. It creates a `studio.toml` from the template. The tool has no default paths:
without a configuration it stops with a clear message.

## Principles

1. **A human decides.** Check scripts and the fact checker only advise. Every rule can be set to `aus` (off), `hinweis`
   (notice) or `sperrt` (blocks); the default is `hinweis`. For each finding a human picks: accept, reject or change. Agents
   never sign off on their own.
2. **Every number keeps its source.** Either a public source with a link or an own measurement with sample size and method in
   [`docs/messungen/`](docs/messungen/).
3. **Only the method.** The skills describe procedures, not a particular person, channel or machine. Examples are fictional:
   the Free City of Musterhafen, Nordlicht Analytik GmbH, Erika and Max Mustermann.
4. **Local first.** Everything runs on your machine. No server, no running costs. Exa, Jina and Tavily are external services:
   your search terms go to these providers.
5. **No paywall circumvention.** `quellen-zugang` lists legal routes (libraries, primary sources, your own subscriptions).

## The workflow

| Step | What happens | Plugin |
|---|---|---|
| Research | primary sources first, search through Exa, read through Jina or Tavily | `recherche`, `jina-lesen`, `tavily-suche` |
| Evidence | three research agents, one independent fact checker, a decision table for the human | `recherche` |
| Script | six slots, one hook, spoken language instead of written language, check scripts with hard limits | `skript` |
| Shoot | teleprompter with one sentence per section, two cameras, audio at 48 kHz | `studio` |
| Edit | sync the cameras, measure clicks, build a DaVinci Resolve timeline from a plan | `studio` |
| Delivery | audio at −14 LUFS, video as H.264 | `studio` |

The detailed guide for shooting and editing is [`docs/so-filme-ich.md`](docs/so-filme-ich.md) (German). The setup there is an
example. Fill in your own values.

## Contributing

```text
git config core.hooksPath .githooks      # before every commit: gitleaks and the block list
uv venv
uv pip install pytest ruff requests -e "plugins/studio/werkzeuge[test]"
uv run --no-sync ruff check .
uv run --no-sync pytest
claude plugin validate --strict .
```

- The `pre-commit` hook runs [gitleaks](https://github.com/gitleaks/gitleaks) and `werkzeuge/scrub/pruefen.py`. The script
  knows public rules (user paths, private networks, key patterns) and, optionally, a private block list at
  `~/.config/oss-scrub/sperrliste.txt`. That list never goes into the repo.
- Third-party skills are linked, not copied: [`docs/fremde-skills.md`](docs/fremde-skills.md).
- Examples stay fictional. No real people with allegations as examples.

## License

- Code, skills, agents, commands and tools: [MIT](LICENSES/MIT.txt)
- Documentation in `docs/` and the READMEs: [CC BY 4.0](LICENSES/CC-BY-4.0.txt)

The per-file mapping is machine-readable in [`REUSE.toml`](REUSE.toml).

The evidence rules in `recherche` are recommendations for careful work. They are not legal advice.
