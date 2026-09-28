# mpq-inspect-action

[![GitHub Marketplace](https://img.shields.io/badge/Marketplace-MPQ%20Inspect-2ea44f?logo=github)](https://github.com/marketplace/actions/mpq-inspect)
[![Release](https://img.shields.io/github/v/release/maluramichael/mpq-inspect-action?sort=semver)](https://github.com/maluramichael/mpq-inspect-action/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A reusable GitHub Action that **opens the MPQ files changed in a pull request,
decodes what's inside, and posts a Markdown summary as a sticky PR comment**, so
you can review a WoW client patch without downloading and unpacking it by hand.

Built for [AzerothCore](https://www.azerothcore.org/) / 3.3.5a client patches
(`patch-*.MPQ`), where the interesting payload is usually a handful of DBC files.

## What it reports

- **File manifest**: every file inside each changed `.MPQ` and its size.
- **`CharBaseInfo.dbc`**: decoded race/class combos, **diffed against the
  standard WotLK matrix**, so newly enabled combos (e.g. *Gnome Priest*,
  *Human Hunter*) are highlighted.
- **`CharStartOutfit.dbc`**: starting gear (item IDs) per race/class/gender,
  listed for the non-standard combos only.
- **Any other `.dbc`**: WDBC header stats (records / fields / record size).
- **Text files** (`.lua`, `.xml`, `.toc`, `.txt`, …): a short preview.
- Unknown binaries just appear in the manifest.

Encrypted archives are handled too: the reader decrypts MPQ file/listfile
encryption (`MPQ_FILE_ENCRYPTED` / `MPQ_FILE_FIX_KEY`), which real client
patches use for their `(listfile)`.

## Usage

Add one workflow to the repo that receives MPQ PRs (see
[`examples/workflow.yml`](examples/workflow.yml)):

```yaml
name: Inspect MPQ patches
on:
  pull_request_target:
    types: [opened, synchronize, reopened]
    paths: ["**/*.MPQ", "**/*.mpq"]
  workflow_dispatch:
    inputs:
      pr: { description: "PR number to inspect", required: true }
permissions:
  contents: read
  pull-requests: write
jobs:
  inspect:
    runs-on: ubuntu-latest
    steps:
      - uses: maluramichael/mpq-inspect-action@main
        with:
          pr-number: ${{ github.event.pull_request.number || github.event.inputs.pr }}
```

No `actions/checkout` step is needed: the action fetches only the changed MPQ
blobs through the GitHub API.

Pin to `@main` for always-latest (no tag bumping), or to a release tag if you
want to freeze a version.

### Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `pr-number` | current PR | PR to inspect / comment on |
| `repository` | current repo | `owner/name` for the PR files API |
| `files` | _(auto)_ | explicit MPQ paths; otherwise changed `*.mpq` are auto-detected |
| `max-mb` | `10` | skip archives larger than this |
| `comment` | `true` | post/update the sticky comment |
| `comment-header` | `mpq-inspect` | sticky-comment identity |
| `github-token` | `github.token` | token for the API + comment |
| `changed-only` | `true` | on a PR update, only inspect MPQs changed by that push |
| `before-sha` / `after-sha` | synchronize event | push range for `changed-only` |

### Only re-runs when an MPQ actually changed

A `pull_request` `paths` filter matches the **whole PR diff**, so once a PR
contains an `.MPQ`, every later push (even an SQL-only fix) would re-trigger the
workflow. With `changed-only: true` (default) the action compares just this
push's range (`before..after`) and, if that push touched no MPQ, **posts
nothing**: the existing comment is left as-is. The first `opened` event and
manual `workflow_dispatch` runs always inspect the full PR.

### Output

- `report`: the generated Markdown (use it in later steps if you don't want the
  built-in comment).

## Why `pull_request_target`?

Fork PRs get a **read-only** token under `pull_request`, so the action couldn't
comment. `pull_request_target` runs in the base repo's context with a writable
token. It is safe here because the action **never checks out the PR's code**: it
fetches only the changed `.MPQ` blobs through the GitHub contents API and parses
them as data. Nothing from the fork is executed, so the usual "pwn request"
surface of `pull_request_target` doesn't apply.

## Extending it

Decoders are pluggable. To support another file that shows up inside MPQs:

1. Add a module under `src/decoders/` with a class exposing
   `matches(filename) -> bool` and `render(filename, data) -> str | None`.
2. Register an instance in `src/decoders/__init__.py` (`DECODERS`, most specific
   first).

`src/mpq_reader.py` isolates the MPQ loader ([mpyq](https://github.com/eagleflo/mpyq),
MIT) plus our own encryption-aware `read_file`. If a patch ever uses a
compression the reader can't handle, swap that one file for a
[StormLib](https://github.com/ladislav-zezula/StormLib)-backed reader (`apt install smpq`):
nothing else changes.

## License

MIT, see [LICENSE](LICENSE).
