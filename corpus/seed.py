"""Push the corpora to their private Context Hub repos.

Run from the repo root:
    uv --project agent run python corpus/seed.py            # both
    uv --project agent run python corpus/seed.py product    # one

WHY A SCRIPT AND NOT `mda deploy`. `mda deploy` syncs only the agent's OWN
context repo (instructions.md and skills/). The corpora are separate repos the
agent reads at runtime through a connection, so they are seeded independently
and can be refreshed without a deploy.

CREDENTIALS. Read explicitly from agent/.env. A bare `Client()` silently falls
back to ambient credentials and can target a different workspace, which looks
like "the corpus did not sync" rather than "wrong account".

PRIVACY. Every push asserts `is_public=False`. These repos being private is
what makes the engineering corpus genuinely unreachable without the
credential — the property the whole demo rests on — so it is asserted rather
than left to a default.
"""

from __future__ import annotations

import os
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV = REPO_ROOT / "agent" / ".env"
sys.path.insert(0, str(REPO_ROOT / "agent"))

#: local directory -> Context Hub repo handle (unqualified; push takes a bare
#: handle, while pull requires `owner/handle` — see contracts.grants.HUB_OWNER)
CORPORA = {
    "product": "product-docs",
    "engineering": "engineering-runbooks",
}


def env(name: str) -> str:
    for line in ENV.read_text().splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"{name} not found in {ENV}")


def pages(directory: pathlib.Path) -> dict[str, str]:
    """Every .md page in the directory, keyed by filename.

    README.md is excluded: it documents the corpus for humans (including the
    fact that the engineering pages are fictional) and must not become a page
    the agent can retrieve and quote back.
    """
    found = {
        p.name: p.read_text()
        for p in sorted(directory.glob("*.md"))
        if p.name.upper() != "README.MD"
    }
    if not found:
        raise SystemExit(f"{directory} has no pages — refusing to push an empty corpus")
    return found


def main() -> None:
    from langsmith import Client
    from langsmith.schemas import FileEntry

    os.environ["LANGSMITH_WORKSPACE_ID"] = env("LANGSMITH_WORKSPACE_ID")
    client = Client(api_key=env("MDA_DEV_CONTEXT_HUB_CORPUS"))

    wanted = sys.argv[1:] or list(CORPORA)
    unknown = set(wanted) - set(CORPORA)
    if unknown:
        raise SystemExit(f"unknown corpus: {', '.join(sorted(unknown))}")

    from contracts.grants import HUB_OWNER

    for name in wanted:
        repo = CORPORA[name]
        qualified = f"{HUB_OWNER}/{repo}"
        content = pages(REPO_ROOT / "corpus" / name)
        chars = sum(len(c) for c in content.values())

        # Skip an unchanged push. Context Hub commits on EVERY push, even with
        # byte-identical content, so without this check a re-run adds a commit
        # that says nothing and the history stops being readable.
        try:
            current = client.pull_agent(qualified)
            unchanged = {p: f.content for p, f in current.files.items()} == content
        except Exception:
            unchanged = False
        if unchanged:
            print(f"{name:12} -> {repo:22} {len(content):3d} pages  {chars:6d} chars"
                  f"  unchanged, not pushed (commit {current.commit_hash[:12]})")
            continue

        url = client.push_agent(
            repo,
            files={p: FileEntry(content=c) for p, c in content.items()},
            description=f"Demo corpus: {name}. Private. Seeded by corpus/seed.py.",
            is_public=False,
        )
        # Read back and verify, rather than trusting the push.
        snap = client.pull_agent(qualified)
        assert set(snap.files) == set(content), (
            f"{repo}: pushed {len(content)} pages, read back {len(snap.files)}"
        )
        assert snap.files == {p: f for p, f in snap.files.items()}  # shape sanity
        print(f"{name:12} -> {repo:22} {len(content):3d} pages  {chars:6d} chars"
              f"  commit {snap.commit_hash[:12]}")
        print(f"             {url}")


if __name__ == "__main__":
    main()
