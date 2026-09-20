"""Enforce the project's language rules at build time.

PLAN.md Phase 8 sets rules for how the site may describe what the data shows. They
exist because the site publishes claims about named living people who have not been
accused of anything, and because the project's credibility is its only real defence.

Rules that depend on discipline get broken eventually — by a tired edit, or by a
contributor who never read the plan. So they are enforced mechanically here and the
build FAILS rather than publishing a violation.

Forbidden: any word asserting wrongdoing.
Required : every page carries the LegiScan attribution its licence demands (D45).
"""

from __future__ import annotations

import re

# Words that assert a conclusion the data cannot support. The site reports patterns;
# determining whether a law was broken belongs to the Registry, the Ethics Commission
# and the courts.
FORBIDDEN = [
    "violated", "violation", "violates", "illegal", "illegally", "unlawful",
    "corrupt", "corruption", "bribe", "bribery", "kickback", "criminal",
    "crime", "fraud", "fraudulent", "guilty", "scandal", "payoff",
    "bought and paid", "in the pocket", "quid pro quo",
]

# Phrases the plan prescribes instead.
PREFERRED = ["flagged for review", "pattern", "exceeds chamber median"]

_WORD = re.compile(r"[a-z][a-z' ]*[a-z]|[a-z]")


def check_text(text: str, where: str) -> list:
    """Return a list of violations. Ignores text inside HTML comments and scripts."""
    stripped = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    stripped = re.sub(r"<script.*?</script>", " ", stripped, flags=re.S | re.I)
    # Bill titles and donor names come from source records and are quoted verbatim;
    # they are evidence, not our prose, so they are exempt.
    stripped = re.sub(r'<[^>]*class="[^"]*\bverbatim\b[^"]*"[^>]*>.*?</[a-z]+>',
                      " ", stripped, flags=re.S | re.I)
    low = stripped.lower()
    found = []
    for word in FORBIDDEN:
        for m in re.finditer(r"\b" + re.escape(word) + r"\b", low):
            snippet = stripped[max(0, m.start() - 60):m.start() + 60].replace("\n", " ")
            found.append(f"{where}: forbidden word {word!r} — ...{snippet.strip()}...")
    return found


def check_attribution(html: str, where: str) -> list:
    """LegiScan data is CC BY 4.0; pages presenting it must credit it (D45)."""
    if "legiscan" not in html.lower():
        return [f"{where}: missing the LegiScan attribution required by CC BY 4.0"]
    return []
