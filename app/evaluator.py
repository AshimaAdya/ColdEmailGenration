import re
from dataclasses import dataclass, field

_SALESY_PHRASES = [
    "i hope this email finds you well",
    "i wanted to reach out",
    "synergy",
    "leverage",
    "utilize",
    "best-in-class",
    "revolutionary",
    "i am excited to",
    "touch base",
    "circle back",
    "game-changer",
    "world-class",
]

_CTA_PATTERN = re.compile(
    r"(15[\s-]?min|call|schedule|chat|connect|calendly|book a|quick sync)",
    re.IGNORECASE,
)


@dataclass
class EvaluationResult:
    passed: bool
    scores: dict = field(default_factory=dict)
    overall_score: float = 0.0
    feedback: str = ""


class EmailEvaluator:
    WEIGHTS = {
        "word_count": 0.10,
        "has_cta": 0.20,
        "tone": 0.20,
        "relevance": 0.10,
        "has_portfolio_link": 0.40,
    }
    PASS_THRESHOLD = 0.7

    def score_word_count(self, email: str) -> tuple[float, str]:
        count = len(email.split())
        if 100 <= count <= 300:
            return 1.0, ""
        if count < 100:
            return 0.0, f"Email is too short ({count} words); aim for 100–300 words."
        return 0.0, f"Email is too long ({count} words); aim for 100–300 words."

    def score_has_cta(self, email: str) -> tuple[float, str]:
        if _CTA_PATTERN.search(email):
            return 1.0, ""
        return 0.0, "No clear call-to-action found; add a suggestion for a 15-min call or meeting."

    def score_tone(self, email: str) -> tuple[float, str]:
        lower = email.lower()
        hits = [p for p in _SALESY_PHRASES if p in lower]
        score = max(0.0, 1.0 - len(hits) * 0.15)
        if hits:
            return score, f"Remove salesy phrases: {', '.join(repr(h) for h in hits[:3])}."
        return 1.0, ""

    def score_relevance(self, email: str, job: dict) -> tuple[float, str]:
        skills = job.get("skills", [])
        if not skills:
            return 1.0, ""
        lower = email.lower()
        matched = [s for s in skills[:8] if s.lower() in lower]
        ratio = len(matched) / min(len(skills), 8)
        if ratio < 0.4:
            missing = [s for s in skills[:4] if s.lower() not in lower]
            return ratio, f"Email barely mentions the job's skills; try referencing: {', '.join(missing)}."
        return ratio, ""

    def score_has_portfolio_link(self, email: str, links: list) -> tuple[float, str]:
        """Check that at least one portfolio URL (flat list of strings) appears in the email."""
        urls = [u for u in links if isinstance(u, str) and u]
        if not urls:
            return 1.0, ""  # no links retrieved — can't penalise

        for url in urls:
            if url in email:
                return 1.0, ""

        return 0.0, f"No portfolio link included; you must embed at least one link from this list: {', '.join(urls)}."

    def evaluate(self, email: str, job: dict, links: list = None) -> EvaluationResult:
        wc_score, wc_fb = self.score_word_count(email)
        cta_score, cta_fb = self.score_has_cta(email)
        tone_score, tone_fb = self.score_tone(email)
        rel_score, rel_fb = self.score_relevance(email, job)
        link_score, link_fb = self.score_has_portfolio_link(email, links or [])

        scores = {
            "word_count": wc_score,
            "has_cta": cta_score,
            "tone": tone_score,
            "relevance": rel_score,
            "has_portfolio_link": link_score,
        }
        overall = sum(scores[k] * self.WEIGHTS[k] for k in scores)
        feedback_parts = [fb for fb in [wc_fb, cta_fb, tone_fb, rel_fb, link_fb] if fb]
        feedback = " ".join(feedback_parts) if feedback_parts else "Email looks good."

        # Hard gate: if links were retrieved but none appear in the email, always fail
        links_available = bool([u for u in (links or []) if isinstance(u, str) and u])
        passed = (overall >= self.PASS_THRESHOLD) and (not links_available or link_score == 1.0)

        return EvaluationResult(
            passed=passed,
            scores=scores,
            overall_score=overall,
            feedback=feedback,
        )
