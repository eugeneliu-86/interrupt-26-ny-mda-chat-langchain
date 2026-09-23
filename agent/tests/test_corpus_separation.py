"""The corpora must be separable, or beat 2 of the demo does not exist.

Every engineering page has a question it exists to answer, and each question is
classified by whether the PRODUCT corpus also covers the topic:

* **beat 2 (clean)** — the product corpus returns nothing above MIN_SCORE, so
  the employee identity, which holds only that corpus, provably cannot answer.
  This is the enforced half of the demo.
* **beat 1 (overlap)** — both corpora answer, and they answer with DIFFERENT
  pages: the product corpus generically, the engineering corpus with team
  policy. This is the "same question, different answers" half.

The classification is asserted in both directions, so a page that moves between
classes fails this test instead of quietly weakening the demo.

Runs offline against the local corpus files: no credential, no network, no LLM.
"""

from __future__ import annotations

import pathlib

import pytest

from tools.search import MIN_SCORE, rank

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent / "corpus"

#: One question per engineering page. Phrased as a person would ask it, not as
#: the page titles it — a question that just echoes the title proves nothing.
ENGINEERING_QUESTIONS = {
    "deploy-to-production.md": "What is our process for deploying an agent to production?",
    "environments.md": "Which environments do we have and what is each one for?",
    "on-call-escalation.md": "What is our on-call escalation path?",
    "break-glass.md": "How do I recover a stuck production deployment?",
    "rotate-a-credential.md": "What is our procedure for rotating a credential?",
    "eval-gate.md": "Do we require evals to pass before merging a prompt change?",
    "dependency-standards.md": "What is our rule on pinning dependency versions?",
    "resilience-standards.md": "Do we require retry middleware on model calls?",
    "observability-standards.md": "Is tracing required in production here?",
    "agent-code-standards.md": "How many approvals does a prompt change need?",
    "documentation-standards.md": "Which documentation domain should we link to?",
    "incident-review.md": "When do we have to write an incident review?",
}


def load(name: str) -> dict[str, str]:
    return {
        p.name: p.read_text()
        for p in sorted((ROOT / name).glob("*.md"))
        if p.name.upper() != "README.MD"
    }


@pytest.fixture(scope="module")
def corpora() -> tuple[dict[str, str], dict[str, str]]:
    return load("product"), load("engineering")


def test_every_engineering_page_has_a_question(corpora):
    """A new page without a question is an unverified page."""
    _, eng = corpora
    assert set(ENGINEERING_QUESTIONS) == set(eng), (
        "every engineering page needs a question in ENGINEERING_QUESTIONS"
    )


@pytest.mark.parametrize("page,question", sorted(ENGINEERING_QUESTIONS.items()))
def test_engineering_question_is_answerable_in_engineering(page, question, corpora):
    _, eng = corpora
    hits = rank(question, eng, 5)
    assert hits, f"{page}: engineering corpus returns nothing for {question!r}"
    assert page in [h[1] for h in hits], (
        f"{page}: expected it in the top 5 for {question!r}; got {[h[1] for h in hits]}"
    )


#: Engineering pages whose TOPIC the product corpus also covers.
#:
#: Determined by measurement, not judgement: `middleware.md` in the product
#: corpus genuinely discusses retry middleware, so a question about our retry
#: requirement hits both corpora. Such pages are beat-1 material — the contrast
#: is generic-versus-ours — and cannot carry beat 2.
PRODUCT_OVERLAP = {"resilience-standards.md"}


@pytest.mark.parametrize(
    "page,question",
    sorted(q for q in ENGINEERING_QUESTIONS.items() if q[0] not in PRODUCT_OVERLAP),
)
def test_beat_2_question_is_unanswerable_in_product(page, question, corpora):
    """The employee holds only productDocs. If this fails, it can answer an
    engineering question and the refusal stops being reliable."""
    prod, _ = corpora
    hits = rank(question, prod, 5)
    assert not hits, (
        f"{page}: product corpus answers {question!r} with "
        f"{[(round(s, 1), p) for s, p, _ in hits]} — either the page now "
        f"overlaps (add it to PRODUCT_OVERLAP) or MIN_SCORE ({MIN_SCORE}) is low"
    )


@pytest.mark.parametrize("page", sorted(PRODUCT_OVERLAP))
def test_beat_1_question_answers_differently_in_each_corpus(page, corpora):
    """An overlapping topic must still produce two DIFFERENT answers: the
    product corpus generically, the engineering corpus with team policy."""
    prod, eng = corpora
    question = ENGINEERING_QUESTIONS[page]
    p_hits, e_hits = rank(question, prod, 3), rank(question, eng, 3)
    assert p_hits, f"{page}: listed as overlapping but product returns nothing"
    assert e_hits, f"{page}: engineering returns nothing for {question!r}"
    assert e_hits[0][1] == page, (
        f"{page}: engineering's top hit is {e_hits[0][1]}, not the page itself"
    )
    assert p_hits[0][1] != e_hits[0][1], (
        f"{page}: both corpora return the same top page — no contrast to show"
    )


def test_overlap_set_is_not_stale(corpora):
    """Every page listed as overlapping must really overlap. A stale entry
    silently exempts a page from the beat-2 check."""
    prod, _ = corpora
    for page in PRODUCT_OVERLAP:
        assert rank(ENGINEERING_QUESTIONS[page], prod, 3), (
            f"{page} is in PRODUCT_OVERLAP but the product corpus no longer "
            f"answers its question — remove it so beat 2 covers the page again"
        )


def test_a_product_question_is_answerable_in_product(corpora):
    """The shared corpus must actually work, or beat 1 has nothing to show."""
    prod, _ = corpora
    for q in ("What is LangGraph?", "How do I install the packages?",
              "How do I set up tracing?"):
        assert rank(q, prod, 3), f"product corpus returns nothing for {q!r}"
