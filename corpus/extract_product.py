"""Extract the productDocs corpus from Chat LangChain Lite's tool data.

WHY THIS EXISTS. `chat-langchain-lite` holds its documentation content as
Python dicts in `agent/tools.py` — six concept entries and four setup guides.
That content is already written, self-contained and public, so it is the
product corpus rather than a curated copy of docs.langchain.com. This removes
the whole llms.txt walk, the page allowlist, and the upstream fetch: the
corpus has no network dependency and cannot drift.

HOW. The source module imports `langchain_core`, so it is parsed with `ast`
and the dict literals are read directly rather than imported. Nothing from the
source module is executed.

Re-runnable: rewrites corpus/product/ from scratch each time.
"""

from __future__ import annotations

import ast
import os
import pathlib
import re
import shutil

CLL = pathlib.Path(os.environ.get(
    "CLL_TOOLS",
    "/Users/eugeneliu/maindrive/code-repos/demos/chat-langchain-lite/agent/tools.py",
))
OUT = pathlib.Path(__file__).parent / "product"

WANTED = ("CONCEPTS_DB", "SETUP_GUIDES_DB")


def literals(path: pathlib.Path) -> dict[str, object]:
    """Read the module-level dict literals we need, without importing."""
    tree = ast.parse(path.read_text())
    found: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in WANTED:
                found[target.id] = ast.literal_eval(node.value)
    missing = set(WANTED) - set(found)
    if missing:
        raise SystemExit(f"{path}: could not find {', '.join(sorted(missing))}")
    return found


#: Proper casing for titles. `str.title()` renders "langgraph" as "Langgraph",
#: which then appears that way in the agent's answers.
DISPLAY = {
    "langchain": "LangChain", "langgraph": "LangGraph", "langsmith": "LangSmith",
    "deep agents": "Deep Agents", "middleware": "Middleware", "tracing": "Tracing",
    "installation": "Installation", "environment": "Environment",
    "deployment": "Deployment", "evaluation": "Evaluation",
}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def title(name: str) -> str:
    return DISPLAY.get(name.lower(), name.title())


def concept_page(name: str, d: dict) -> str:
    """One concept as a page. Title first, then the facts, then the summary."""
    return "\n".join([
        f"# {title(name)}",
        "",
        f"> {d['tagline']}",
        "",
        "| | |",
        "|---|---|",
        f"| Package | `{d['package']}` |",
        f"| First released | {d['first_released']} |",
        f"| Minimum Python | {d['min_python']} |",
        f"| Primary use case | {d['primary_use_case']} |",
        "",
        d["summary"],
        "",
    ])


def guide_page(topic: str, body: str) -> str:
    return f"# {title(topic)}\n\n{body.strip()}\n"


def main() -> None:
    data = literals(CLL)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    written = []
    for name, d in data["CONCEPTS_DB"].items():           # type: ignore[union-attr]
        p = OUT / f"{slug(name)}.md"
        p.write_text(concept_page(name, d))
        written.append(p.name)
    for topic, body in data["SETUP_GUIDES_DB"].items():   # type: ignore[union-attr]
        p = OUT / f"{slug(topic)}.md"
        p.write_text(guide_page(topic, body))
        written.append(p.name)

    print(f"source: {CLL}")
    print(f"wrote {len(written)} pages to {OUT}:")
    for n in sorted(written):
        print(f"  {n:22} {len((OUT / n).read_text()):5d} bytes")


if __name__ == "__main__":
    main()
