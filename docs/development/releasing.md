# CI and releasing

Continuous integration checks every change automatically. Releasing turns a commit into a version
that users can `pip install`. Both run on [GitHub Actions](https://docs.github.com/en/actions),
configured in `.github/workflows/`.

## Concepts

### Continuous integration (CI)

Every push and pull request triggers a fresh machine that installs the project from scratch and
runs all the checks. It catches what local runs miss: a file you forgot to commit, a lockfile not
updated, code that only works on your OS or your Python version. `main` only receives changes that
passed, which keeps it always releasable.

### GitHub Actions vocabulary

```yaml
name: CI                      # workflow: one YAML file in .github/workflows/
on: [push, pull_request]      # events that trigger it
jobs:
  test:                       # job: runs on its own fresh virtual machine
    runs-on: ubuntu-latest    # runner: the machine type
    strategy:
      matrix:                 # matrix: run the job once per combination
        python: ["3.11", "3.12"]
    steps:                    # steps: run in order, the job fails at the first failing step
      - uses: actions/checkout@v4     # action: a reusable step published by someone
      - run: uv run pytest            # run: a shell command
```

- Jobs run **in parallel** unless one declares `needs: <other job>`.
- Jobs do not share files. To pass build output from one job to another, upload it as an
  **artifact** in one job and download it in the next.
- **Secrets** (encrypted, hidden in logs) and **variables** (plain configuration) are set in the
  repository settings and read as `${{ secrets.NAME }}` / `${{ vars.NAME }}`.
- An **environment** (repository settings, *Environments*) groups secrets and can add protection
  rules, such as requiring a manual approval before a job using it runs.
- `permissions` limits what the job's automatic GitHub token may do. Here, everything is read-only
  by default.

### Package indexes

An **index** is a server that hosts distributions. [PyPI](https://pypi.org) is the default one
that `pip` and `uv` use. [TestPyPI](https://test.pypi.org) is a separate playground instance for
practising releases. Companies often run a **private index** (devpi, Nexus, Artifactory, or the
package registries of GitLab, GitHub, Azure, AWS) for internal packages.

Two rules of PyPI matter for releasing:

- **A version can be uploaded only once.** Even after deleting it, the same file name can never be
  reused. A broken release is fixed by publishing a new version (and optionally *yanking* the bad
  one, which hides it from installers without breaking existing pins).
- **Local version labels are rejected.** Versions like `0.1.1.dev3+g1a2b3c4` (an untagged build,
  see [Versioning](pyproject.md#versioning)) cannot be uploaded, which prevents accidental releases.

### Version numbers: SemVer

Versions follow [Semantic Versioning](https://semver.org/), `MAJOR.MINOR.PATCH`:

| Change | Bump | Example |
| --- | --- | --- |
| Incompatible API change | MAJOR | `1.4.2` → `2.0.0` |
| New feature, backwards-compatible | MINOR | `1.4.2` → `1.5.0` |
| Bug fix only | PATCH | `1.4.2` → `1.4.3` |

Before `1.0.0`, the API is considered unstable: breaking changes bump MINOR (`0.3.0` → `0.4.0`).
Pre-releases use PEP 440 suffixes: `0.1.0a1` (alpha), `0.1.0b1` (beta), `0.1.0rc1` (release
candidate). Installers ignore pre-releases unless asked (`pip install --pre`).

### Trusted Publishing

Uploading to PyPI traditionally needed an API token stored as a CI secret, which can leak and never
expires. With [Trusted Publishing](https://docs.pypi.org/trusted-publishers/), you tell PyPI once
"releases of `elm327` come from workflow `release.yml` in repository X, environment `pypi`". When
that workflow runs, GitHub issues it a short-lived signed identity token (OIDC), and PyPI accepts
it. No long-lived secret exists anywhere.

## In this project

### `ci.yml`: every push and pull request

Four jobs run in parallel:

| Job | Does | Catches |
| --- | --- | --- |
| `lint` | `ruff format --check`, `ruff check`, `mypy` | style, lint and type errors |
| `test` | `pytest --cov` on 3 OSes × 4 Python versions (12 runs) | OS or version-specific bugs, coverage below 90% |
| `docs` | `mkdocs build --strict` | broken links and references in the docs |
| `build` | `uv build`, then installs the wheel in a clean environment and imports it | packaging mistakes, e.g. a file missing from the wheel |

Details worth knowing:

- Every job starts with `uv sync --locked`, so CI uses exactly the versions in `uv.lock` and fails
  if the lockfile is stale.
- `fail-fast: false` lets every matrix combination finish, so one failure shows the whole picture
  (e.g. "fails on Windows only").
- `concurrency` cancels an older run of the same branch when you push again.
- The `build` job checks out with `fetch-depth: 0` (full history and tags), because hatch-vcs needs
  the tags to compute the version.
- `workflow_call` makes the CI workflow reusable, so the release workflow can run it first.

### `release.yml`: on a version tag

```text
push tag v0.1.0
      │
      ▼
   ci (the whole ci.yml) ──▶ build (once) ──┬──▶ pypi            if PUBLISH_TO_PYPI = true
                                            └──▶ private-index   if PRIVATE_INDEX_URL is set
```

1. **ci**: a release can never skip the checks.
2. **build**: the sdist and wheel are built **once** and uploaded as an artifact. Every target
   receives byte-identical files.
3. **pypi**: downloads the artifact and publishes with Trusted Publishing
   (`pypa/gh-action-pypi-publish`). It runs in the `pypi` environment and is the only job allowed to
   request an identity token (`id-token: write`).
4. **private-index**: downloads the artifact and runs `uv publish` with the URL from the
   `PRIVATE_INDEX_URL` variable and credentials from secrets, in the `private-index` environment.

Both publishing jobs are switched off until you configure them, so pushing a tag before the setup
is harmless: it only builds.

### One-time setup

**PyPI**

1. Create an account on [pypi.org](https://pypi.org) and enable two-factor authentication.
2. Under *Your account → Publishing*, add a **pending publisher** (it reserves the name before the
   first upload): project `elm327`, your GitHub owner and repository, workflow `release.yml`,
   environment `pypi`.
3. In the GitHub repository settings, create the environment `pypi` (optionally requiring your
   approval) and the repository variable `PUBLISH_TO_PYPI` = `true`.

**Private index**

1. Repository variable `PRIVATE_INDEX_URL`: the index's *upload* URL (it differs from the URL used
   to install; check your server's documentation).
2. Environment `private-index` with secrets `PRIVATE_INDEX_USERNAME` and `PRIVATE_INDEX_PASSWORD`
   (for token-based servers: the username they document, often `__token__`, and the token).

Users then install from it with, for example:

```bash
pip install --index-url https://your.server/simple/ elm327
```

### Practising on TestPyPI

The first time, rehearse by hand on TestPyPI. It needs its own account and an API token
(*Account settings → API tokens*). Commit everything first: uncommitted changes add a `.d<date>`
label to the version, which the index rejects.

```bash
git tag v0.1.0rc1                 # a pre-release tag gives a clean, uploadable version
uv build
uv publish --publish-url https://test.pypi.org/legacy/ --token <testpypi-token>
git tag -d v0.1.0rc1              # the tag was only needed for the build
```

Then install it in a throwaway environment. TestPyPI is added *next to* PyPI, because
dependencies such as pyserial are only on the real PyPI:

```bash
uv run --isolated --no-project --index https://test.pypi.org/simple/ --index-strategy unsafe-best-match --with elm327==0.1.0rc1 python -c "import elm327; print(elm327.__version__)"
```

### Release checklist

1. `main` is green in CI.
2. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [0.1.0] - YYYY-MM-DD` and add a fresh empty
   `## [Unreleased]` above it. Commit: `docs: release 0.1.0`.
3. Tag that commit and push the tag:
   ```bash
   git tag -a v0.1.0 -m "Release 0.1.0"
   git push origin v0.1.0
   ```
4. Watch the *Release* workflow in the *Actions* tab. Approve the deployment if the environment
   requires it.
5. Check the PyPI page, and install the release in a clean environment.
6. Optionally create a GitHub Release from the tag, pasting the changelog section.

A tag must point to a commit that is on `main`; release from `main`, never from a feature branch.
