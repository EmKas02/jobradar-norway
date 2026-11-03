"""Score job ads against a candidate profile.

The score (0-100) is a transparent blend of:
  * skill coverage  - how many of the profile's skills the ad mentions
  * text similarity - TF-IDF cosine similarity between profile and ad
  * role fit        - data/analytics wording in the title
  * level fit       - bonus for junior/graduate wording, penalty for senior
                      and academic (PhD/researcher) roles
Every component is returned so the report can explain each score.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_ROLE = re.compile(r"data|analy|statisti|\bbi\b|business intelligence|machine learning|maskinlæring|\bml\b|\bai\b|insight|innsikt", re.I)
_JUNIOR = re.compile(r"junior|graduate|trainee|nyutdannet|newly graduated|entry.level|internship|\bintern\b|sommerstudent|summer student|lærling", re.I)
_SENIOR = re.compile(r"senior|\blead\b|principal|leder|manager|head of|direktør|director|sjef|ekspert|expert", re.I)
_ACADEMIC = re.compile(r"\bphd\b|ph\.d|stipendiat|postdoc|professor|lektor|forsker|researcher|research fellow", re.I)
_LANGUAGES = ("german", "spanish", "french", "dutch", "swedish", "danish", "italian", "portuguese", "finnish", "polish", "russian", "ukrainian", "arabic", "turkish")
_YEARS = re.compile(r"(\d+)\s*\+?\s*(?:-\s*\d+\s*)?(?:års|år|years?)(?:\s+(?:relevant\s+)?(?:erfaring|experience|of experience))", re.I)


@dataclass
class Match:
    score: int
    skills: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


def _alias_pattern(alias: str) -> re.Pattern:
    return re.compile(rf"(?<![\w]){re.escape(alias)}(?![\w])", re.I)


class Matcher:
    def __init__(self, profile: dict):
        self.profile_text = " ".join([profile.get("summary", ""), " ".join(profile.get("skills", {}))])
        self.skills = {
            name: [_alias_pattern(a) for a in (aliases or [name])]
            for name, aliases in profile.get("skills", {}).items()
        }
        self.skill_target = profile.get("skill_target", 5)
        spoken = {l.lower() for l in profile.get("languages", ["english", "norwegian"])}
        other = "|".join(l for l in _LANGUAGES if l not in spoken)
        # "fluent German", "Russian (fluent)", "Spanish-speaking", "German (C1)", or German job-ad conventions.
        self.other_language = re.compile(
            rf"\b(?:fluent|native|business[- ]level|excellent|proficient|strong|good)\b[^.\n]{{0,30}}\b(?:{other})\b"
            rf"|\b(?:{other})\b[^.\n]{{0,15}}\(fluent|\b(?:{other})[- ]speaking\b|\b(?:{other})\s*\(?c[12]\b|\bm/w/d\b|\bwerkstudent\b",
            re.I,
        ) if other else None

    def score_many(self, ads: list[dict]) -> list[Match]:
        """Score ads in one pass so TF-IDF weights come from the whole batch."""
        if not ads:
            return []
        docs = [f"{a['title']} {a['text']}" for a in ads]
        vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)
        matrix = vec.fit_transform([self.profile_text, *docs])
        sims = cosine_similarity(matrix[0], matrix[1:]).ravel()
        return [self._score(ad, doc, sim) for ad, doc, sim in zip(ads, docs, sims)]

    def _score(self, ad: dict, doc: str, sim: float) -> Match:
        title = ad["title"]
        skills = [name for name, pats in self.skills.items() if any(p.search(doc) for p in pats)]
        flags: list[str] = []

        score = 45 * min(1.0, len(skills) / self.skill_target)
        score += 25 * min(1.0, sim / 0.15)
        if _ROLE.search(title):
            score += 15
            flags.append("data role")
        if _JUNIOR.search(doc):
            score += 15
            flags.append("entry level")
        if _SENIOR.search(title):
            score -= 30
            flags.append("senior title")
        if _ACADEMIC.search(title):
            score -= 30
            flags.append("academic post")
        years = [int(n) for n in _YEARS.findall(doc)]
        if years and max(years) >= 3:
            score -= 15
            flags.append(f"asks {max(years)}+ yrs")
        if self.other_language and self.other_language.search(doc):
            score -= 25
            flags.append("needs other language")
        if ad.get("remote"):
            flags.append("remote")

        return Match(score=int(max(0, min(100, round(score)))), skills=skills, flags=flags)
