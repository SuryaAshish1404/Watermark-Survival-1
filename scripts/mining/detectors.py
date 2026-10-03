"""Operation-class detectors, derived from repository/workflow configuration files.

Per the study design: the catalogue must be *mined*, not invented.
Every entry here is a claim of the form "if config signal X is present, operation
class Y is configured in this repo" — and the scanner (scan.py) always records which
file produced the match, so every catalogue entry traces to a cited configuration
file (the acceptance criterion in the brief's technical task table).

Adding an operation class means adding a detector here with real glob/content
evidence, not editing the catalogue output directly.

Two kinds of evidence, deliberately kept separate:
- `exist_globs`: files whose mere existence is dedicated enough to count as
  evidence on its own (a `.prettierrc` file is never present for an unrelated
  reason).
- `content_globs` + `content_pattern`: generic, multi-purpose files (package.json,
  workflow YAML, Makefile, pyproject.toml, ...) where existence alone proves
  nothing — the regex must also match somewhere inside.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OperationSignal:
    id: str
    layer: str  # "history" | "source" | "packaging"
    description: str
    exist_globs: tuple[str, ...] = field(default_factory=tuple)
    content_globs: tuple[str, ...] = field(default_factory=tuple)
    content_pattern: str | None = None
    # Keywords used to classify a CI workflow *step* as an instance of this
    # operation, for observed-order extraction (workflow_order.py). Matched
    # case-insensitively against the step's `name` and `run` fields.
    step_keywords: tuple[str, ...] = field(default_factory=tuple)


# --- History layer -----------------------------------------------------------

SQUASH_MERGE = OperationSignal(
    id="squash_merge",
    layer="history",
    description="Repo configured for squash-merge PRs (squash-only or squash allowed)",
    content_globs=(".github/settings.yml", ".github/*.yml"),
    content_pattern=r"squash",
    step_keywords=("squash",),
)

REBASE = OperationSignal(
    id="rebase",
    layer="history",
    description="Rebase-based workflow (rebase-merge allowed, or rebase configured as pull strategy)",
    content_globs=(".gitconfig", ".github/settings.yml", ".github/*.yml"),
    content_pattern=r"rebase",
    step_keywords=("rebase",),
)

CHERRY_PICK = OperationSignal(
    id="cherry_pick",
    layer="history",
    description="Automated cherry-pick / backport workflow",
    content_globs=(".github/workflows/*.yml", ".github/workflows/*.yaml"),
    content_pattern=r"cherry[-_ ]?pick|backport",
    step_keywords=("cherry-pick", "cherry pick", "backport"),
)

FORK_SYNC = OperationSignal(
    id="fork_sync",
    layer="history",
    description="Upstream fork-sync workflow (evidence of a fork-based contribution model)",
    content_globs=(".github/workflows/*.yml", ".github/workflows/*.yaml"),
    content_pattern=r"sync[-_ ]?fork|upstream[-_ ]?sync",
    step_keywords=("sync fork", "upstream sync"),
)

# --- Source layer --------------------------------------------------------------

FORMAT = OperationSignal(
    id="format",
    layer="source",
    description="Code formatter configured (prettier, black, gofmt, rustfmt, etc.)",
    exist_globs=(".prettierrc*", "prettier.config.*", ".editorconfig"),
    content_globs=("pyproject.toml", ".github/workflows/*.yml", ".github/workflows/*.yaml"),
    content_pattern=r"prettier|black\s*=|gofmt|rustfmt|\bformat\b",
    step_keywords=("format", "prettier", "black", "gofmt", "rustfmt"),
)

LINT_AUTOFIX = OperationSignal(
    id="lint_autofix",
    layer="source",
    description="Lint autofix configured (eslint --fix, ruff --fix, pre-commit autofix hooks)",
    exist_globs=(".eslintrc*", ".pre-commit-config.yaml", "ruff.toml"),
    content_globs=("pyproject.toml", ".github/workflows/*.yml", ".github/workflows/*.yaml"),
    content_pattern=r"--fix\b|eslint|ruff\s*=|pre-commit",
    step_keywords=("lint", "eslint", "ruff", "--fix"),
)

TRANSPILE = OperationSignal(
    id="transpile",
    layer="source",
    description="Transpilation configured (Babel, tsc target, SWC)",
    exist_globs=("babel.config.*", ".babelrc*", "tsconfig.json", ".swcrc"),
    step_keywords=("babel", "tsc", "transpile", "swc"),
)

BUNDLE = OperationSignal(
    id="bundle",
    layer="source",
    description="Bundler configured (webpack, rollup, esbuild, vite)",
    exist_globs=("webpack.config.*", "rollup.config.*", "esbuild.config.*", "vite.config.*"),
    step_keywords=("webpack", "rollup", "esbuild", "vite build", "bundle"),
)

MINIFY = OperationSignal(
    id="minify",
    layer="source",
    description="Minification configured (terser, uglify, production bundler mode)",
    exist_globs=("terser.config.*",),
    content_globs=("webpack.config.*", "vite.config.*"),
    content_pattern=r"minify|terser|uglify|mode:\s*['\"]?production",
    step_keywords=("minify", "terser", "uglify"),
)

# --- Packaging layer -----------------------------------------------------------

REBUILD = OperationSignal(
    id="rebuild",
    layer="packaging",
    description="CI build step that rebuilds from source",
    content_globs=(".github/workflows/*.yml", ".github/workflows/*.yaml", "Makefile"),
    content_pattern=r"\bbuild\b|\bmake\b",
    step_keywords=("build", "compile", "make"),
)

REPACKAGE = OperationSignal(
    id="repackage",
    layer="packaging",
    description="Artifact repackaging configured (Docker image build, sdist/bdist, jar packaging)",
    exist_globs=("Dockerfile",),
    content_globs=("setup.py", "pyproject.toml", ".github/workflows/*.yml", ".github/workflows/*.yaml"),
    content_pattern=r"docker\s+build|sdist|bdist|package\b",
    step_keywords=("docker build", "package", "sdist", "bdist"),
)

REPUBLISH = OperationSignal(
    id="republish",
    layer="packaging",
    description="Release/publish workflow configured (npm publish, PyPI upload, GitHub Release, GoReleaser, PPA/dput, AppImage upload)",
    exist_globs=(".goreleaser.yml", ".releaserc*"),
    content_globs=(".github/workflows/*.yml", ".github/workflows/*.yaml"),
    content_pattern=r"npm publish|pypi|twine upload|softprops/action-gh-release|goreleaser|semantic-release|\bdput\b|ppa|appimage",
    step_keywords=("publish", "release", "npm publish", "goreleaser", "dput", "ppa"),
)

ALL_SIGNALS: tuple[OperationSignal, ...] = (
    SQUASH_MERGE, REBASE, CHERRY_PICK, FORK_SYNC,
    FORMAT, LINT_AUTOFIX, TRANSPILE, BUNDLE, MINIFY,
    REBUILD, REPACKAGE, REPUBLISH,
)
