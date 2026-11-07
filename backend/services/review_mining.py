"""
Aspect-based sentiment mining (ABSA) over stored review text.

`sentiment_analysis.SentimentAnalysisService` scores a whole review and stores a
per-aspect *label* at ingest time. It answers "how does this aspect score?".
This module answers the question the dashboard could not answer before: *why* —
the concrete clause of the review that mentions an aspect, carrying the polarity
that clause itself expresses.

Two properties are load-bearing and are enforced by construction:

1. **Nothing is invented.** Every `phrase` returned is a verbatim clause of one
   of the reviews in its `review_ids` (whitespace collapsed, surrounding
   punctuation trimmed). The group is the set of reviews whose clause is
   near-identical — the same content words — so the phrase is the group's
   representative wording, not a paraphrase. A review whose text contains no
   aspect keyword produces no reason at all; an empty list is the honest
   answer, never a fabricated phrase.
2. **Every count is computed.** `mentions` is the number of distinct reviews in
   the group, and `review_ids` is exactly those reviews, so
   `mentions == len(review_ids)` always holds.

The extraction is deterministic: the same reviews always produce the same
phrases in the same order (sorting is by mentions desc, then phrase asc).

How a reason is decided
-----------------------
A review is split into sentences, then into clauses at punctuation (`,` `;` `:`)
and at the contrast conjunctions `but` / `dar`. A clause is attributed to every
aspect whose keyword pattern it contains. The clause's polarity is the VADER
compound score of that clause, computed with a domain lexicon (tech English plus
the Romanian vocabulary the corpus actually uses), and read with the same
+/-0.05 thresholds the rest of the codebase uses. A clause that mentions an
aspect but carries no lexicon signal is `neutral` — it is still reported,
because the mention is real even when the tone is not.

Known limits, stated rather than hidden: this is a lexicon method, not a trained
model. It cannot resolve sarcasm, and a word whose polarity depends on the noun
it modifies ("mare" = large, negative only when it modifies a price) is handled
by a small aspect-conditioned table, not by grammar.
"""
import logging
import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger("marketpulse.services.review_mining")

# Display labels. The eight stored aspects keep the wording the Sentiment page
# already uses; `thermals` is new here because the review corpus talks about
# heat and temperatures and the stored aspect set has no home for them.
ASPECT_LABELS = {
    "battery": "Battery life",
    "camera": "Camera quality",
    "display": "Display",
    "performance": "Performance",
    "price_value": "Price & value",
    "build_quality": "Build quality",
    "software": "Software & OS",
    "audio": "Audio",
    "thermals": "Thermals",
}

# Keyword patterns per aspect. Deliberately broader than the ingest-time
# patterns in `sentiment_analysis.py`: the stored table only needs a yes/no per
# sentence, while mining needs to catch the inflected Romanian forms the corpus
# actually contains ("bateria", "ecranul", "pretul", "sunetul").
ASPECT_PATTERNS: Dict[str, List[str]] = {
    "battery": [
        r"\bbatter(y|ies)\b", r"\bautonomi(a|e|ei)\b", r"\bcharg(e|es|ed|ing)\b",
        r"\bincarcar(e|ea|ii)\b", r"\bbateri(a|e|ei)\b",
    ],
    "camera": [
        r"\bcameras?\b", r"\bphotos?\b", r"\bfoto\b", r"\bpoze\b", r"\blens\b",
        r"\bsenor\b", r"\bvideo\b", r"\bzoom\b(?!\s*calls?\b)",
    ],
    "display": [
        r"\bdisplay\b", r"\becran(ul)?\b", r"\bscreen\b", r"\boled\b",
        r"\bamoled\b", r"\b120hz\b", r"\brefresh rate\b",
    ],
    "performance": [
        r"\bperformance\b", r"\bperformant(a|e)\b", r"\bspeed\b", r"\bviteza\b",
        r"\bprocessors?\b", r"\bprocesor(ul)?\b", r"\bcpu\b", r"\bgpu\b",
        r"\bram\b", r"\bfps\b", r"\bchip(ul)?\b",
    ],
    "price_value": [
        r"\bprices?\b", r"\bpret(ul|uri|urile)?\b", r"\bvalue\b", r"\bcost\b",
        r"\bexpensive\b", r"\boverpriced\b", r"\bscump(a|e)?\b",
        r"\bieftin(a|e)?\b", r"\bworth\b",
    ],
    "build_quality": [
        r"\bbuild\b", r"\bdesign\b", r"\bconstructi(a|e)\b", r"\bmaterials?\b",
        r"\bmateriale\b", r"\bweight\b", r"\bgreutate\b", r"\bgreu\b",
    ],
    "software": [
        r"\bsoftware\b", r"\bos\b", r"\bios\b", r"\bandroid\b", r"\bwindows\b",
        r"\bui\b", r"\bupdates?\b", r"\baplicati(a|e)\b", r"\bapplications?\b",
        r"\binterface\b",
    ],
    "audio": [
        r"\baudio\b", r"\bsound\b", r"\bsunet(ul)?\b", r"\bspeakers?\b",
        r"\bdifuzor(ul)?\b", r"\bmicrophones?\b", r"\bmic\b", r"\bbass\b",
        r"\banc\b", r"\bnoise\b", r"\bzgomot(ul)?\b", r"\bheadphones?\b",
    ],
    "thermals": [
        r"\btemperatur(a|i|ile|ilor)\b", r"\bthermals?\b", r"\bheat(s|ing)?\b",
        r"\boverheat(ing|ed)?\b", r"\bincalzire\b", r"\bsupraincalzire\b",
        r"\bcool(ing)?\b", r"\bracire\b",
    ],
}

# A keyword that only appears inside a comparison is not a statement about the
# product's own aspect: "lenta comparativ cu Android" is not a software problem.
ASPECT_SUPPRESSORS: Dict[str, List[str]] = {
    "software": [r"\b(comparativ cu|compared to|than)\s+(android|ios|windows)\b"],
    # "charging speed" is a battery statement; the generic "speed" keyword would
    # otherwise also file it under performance.
    "performance": [r"\b(charging|charge|incarcare|incarcarea)\s+speed\b"],
}

# VADER's English lexicon is missing many everyday adjectives the corpus uses
# ("slow", "quiet", "decent"), and scores "unmatched" negative. These entries
# are plain domain vocabulary, not corpus-specific tuning: each one carries the
# polarity it has in a product review.
BASE_LEXICON: Dict[str, float] = {
    # English adjectives VADER does not know.
    "slow": -1.6, "slower": -1.6, "fast": 1.8, "faster": 1.8,
    "quiet": 1.4, "quieter": 1.4, "silent": 1.4,
    "decent": 1.0, "minimal": 0.8, "sharp": 1.2, "usable": 1.0,
    "issue": -1.4, "expensive": -2.0, "unmatched": 2.4,
    # "charges" is a noun here ("three days between charges"); VADER reads the
    # verb and scores it -1.1.
    "charge": 0.0, "charges": 0.0, "charging": 0.0,
    # "noise cancelling" is a feature, not a complaint.
    "cancelling": 1.0, "canceling": 1.0,
    # Tech vocabulary shared with the ingest-time lexicon.
    "lag": -1.4, "laggy": -2.8, "stutter": -2.0, "overheating": -3.0,
    "overheat": -2.8, "throttling": -2.2, "bloatware": -2.4,
    "overpriced": -2.5, "buggy": -2.6, "drain": -1.5, "drains": -1.5,
    "crisp": 2.2, "fluid": 2.5, "snappy": 2.8, "beast": 3.0,
    "flagship": 2.0, "stunning": 3.2, "masterpiece": 3.5, "worth": 2.0,
    "premium": 2.6, "durable": 2.5,
    # Romanian vocabulary the corpus uses.
    "excelent": 2.8, "excelenta": 2.8, "excelente": 2.8,
    "bun": 1.8, "buna": 1.8, "bune": 1.8, "superb": 2.8, "superba": 2.8,
    "uimitor": 3.0, "uimitoare": 3.0, "uluitoare": 2.8,
    "impresionant": 2.6, "impresionanta": 2.6,
    "incredibil": 2.8, "incredibila": 2.8, "impecabil": 2.6,
    "perfect": 2.6, "perfecta": 2.6, "capodopera": 3.5,
    "rapid": 1.9, "rapida": 1.9, "silentios": 1.8, "silentioasa": 1.8,
    "usor": 1.4, "usoara": 1.4, "confortabil": 1.9, "confortabile": 1.9,
    "echilibrat": 1.8, "clar": 1.6, "clara": 1.6, "luminos": 1.8,
    "natural": 1.6, "naturale": 1.6, "util": 1.5, "utila": 1.5,
    "practic": 1.5, "bine": 1.7, "multumit": 2.0, "multumita": 2.0,
    "recomand": 2.0, "merita": 1.8, "rezonabil": 1.6,
    "redus": 1.3, "redusa": 1.3, "scazute": 1.3, "constant": 1.4,
    "stabil": 1.6, "apreciat": 2.0, "apreciata": 2.0, "tine": 1.5,
    "scump": -2.2, "scumpa": -2.2, "scumpe": -2.2,
    "slab": -2.2, "slaba": -2.2, "lent": -1.9, "lenta": -1.9,
    "problema": -2.0, "probleme": -2.0, "dezamagitor": -2.6,
    "voluminos": -1.6, "voluminoasa": -1.6, "lipsa": -1.8, "lipsesc": -1.8,
    "incalzire": -1.8, "supraincalzire": -2.6, "dificil": -1.8,
    "complicat": -1.8, "zgomotos": -1.8,
}

# Words whose polarity depends on the aspect they describe. "mare" means large;
# it is a complaint only when it modifies a price. "greu" means heavy; it is a
# complaint only when it describes the device itself.
ASPECT_TERMS: Dict[str, Dict[str, float]] = {
    "price_value": {
        "mare": -2.0, "mari": -2.0, "high": -1.5,
        "piperat": -2.0, "piperata": -2.0,
    },
    "build_quality": {"greu": -1.6},
    # "minimal drain" is praise: the bad thing is small.
    "battery": {"minimal": 2.0},
}

# Romanian negations. VADER only negates English words, and its negation list is
# module-global, so it is applied here, to the clause, rather than by mutating
# the shared analyzer.
NEGATION_PATTERN = re.compile(r"\b(fara|nu|nici)\b", re.IGNORECASE)

# "could be faster" is a wish for improvement, i.e. a criticism, even though
# VADER reads "faster" as positive. The pattern is deliberately narrow.
COUNTERFACTUAL_PATTERN = re.compile(
    r"\b(?:could|would|should)\s+be\s+"
    r"(?:faster|better|cheaper|higher|lower|simpler|smaller|lighter|quieter|sharper)\b",
    re.IGNORECASE,
)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
CLAUSE_SPLIT = re.compile(r"[,;:]+|\s+(?:but|dar)\s+", re.IGNORECASE)
TOKEN = re.compile(r"[a-zăâîșț0-9][a-zăâîșț0-9\-]*")

# Discourse markers that open a clause without carrying meaning. They are
# stripped from the displayed phrase, which stays a verbatim substring.
LEADING_CONNECTOR = re.compile(
    r"^(?:and|but|or|so|yet|though|although|however|while|whereas|"
    r"dar|iar|insa|totusi|si)\s+",
    re.IGNORECASE,
)

# Function words dropped from the dedupe signature. Negations are deliberately
# absent: "battery is good" and "battery is not good" must never collapse.
SIGNATURE_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "it", "its",
    "this", "that", "these", "those", "of", "to", "in", "on", "at", "for",
    "with", "and", "or", "as", "by", "from", "my", "our", "your", "their",
    "i", "we", "you", "they", "very", "quite", "really", "so", "too", "also",
    "just", "still", "even", "though", "however", "while",
    "si", "sau", "dar", "iar", "insa", "totusi", "este", "sunt", "foarte",
    "mai", "cel", "cea", "care", "pentru", "din", "cu", "pe", "la", "un", "o",
    "al", "ale", "lui", "ei", "se", "de", "ca", "sa", "fost", "am", "ai",
    "are", "avea", "ma", "mi", "il", "le", "niste", "cam", "destul", "deja",
})


class ReviewMiningService:
    """Extracts aspect reasons, recurring problems and recurring praise."""

    def __init__(self) -> None:
        # One analyzer per aspect, so a clause is scored with the vocabulary
        # that aspect actually uses. Built once; never mutated afterwards.
        self._analyzers: Dict[str, SentimentIntensityAnalyzer] = {}
        for aspect in ASPECT_PATTERNS:
            analyzer = SentimentIntensityAnalyzer()
            analyzer.lexicon.update(BASE_LEXICON)
            analyzer.lexicon.update(ASPECT_TERMS.get(aspect, {}))
            self._analyzers[aspect] = analyzer

    # ------------------------------------------------------------------ #
    # Text primitives
    # ------------------------------------------------------------------ #

    @staticmethod
    def _clauses(text: str) -> List[str]:
        """Sentence, then clause split. Order is the review's own order."""
        out: List[str] = []
        for sentence in SENTENCE_SPLIT.split(text or ""):
            sentence = sentence.strip()
            if not sentence:
                continue
            for part in CLAUSE_SPLIT.split(sentence):
                part = part.strip(" \t\"'()[]")
                if part:
                    out.append(part)
        return out

    @staticmethod
    def _aspects_in(clause: str) -> List[str]:
        low = clause.lower()
        found = []
        for aspect, patterns in ASPECT_PATTERNS.items():
            if not any(re.search(p, low) for p in patterns):
                continue
            suppressors = ASPECT_SUPPRESSORS.get(aspect, [])
            if any(re.search(p, low) for p in suppressors):
                continue
            found.append(aspect)
        return found

    def _polarity(self, clause: str, aspect: str) -> str:
        if COUNTERFACTUAL_PATTERN.search(clause):
            return "negative"
        compound = self._analyzers[aspect].polarity_scores(clause)["compound"]
        if NEGATION_PATTERN.search(clause):
            compound = -compound
        if compound >= 0.05:
            return "positive"
        if compound <= -0.05:
            return "negative"
        return "neutral"

    @staticmethod
    def _display(phrase: str) -> str:
        """The phrase as it will be shown: verbatim, whitespace collapsed."""
        collapsed = re.sub(r"\s+", " ", phrase).strip(" \t\"'()[],;:.")
        return LEADING_CONNECTOR.sub("", collapsed).strip(" \t\"'()[],;:.")

    @staticmethod
    def _signature(phrase: str) -> Tuple[str, ...]:
        """
        Dedupe key: the content words of the phrase, sorted.

        Two phrasings that differ only in function words ("the price is high" /
        "price is high") therefore count as one reason. Negations are content
        words here, so opposite statements never merge.
        """
        tokens = [t for t in TOKEN.findall(phrase.lower()) if t not in SIGNATURE_STOPWORDS]
        return tuple(sorted(tokens))

    # ------------------------------------------------------------------ #
    # Mining
    # ------------------------------------------------------------------ #

    def mine(self, reviews: Sequence[Any]) -> Dict[str, Any]:
        """
        Mine a sequence of Review-like objects (`id` and `content` attributes).

        Returns the response payload: aspects with their reasons, the recurring
        problems and praise across all aspects, and the coverage block.

        Each reason's `phrase` is a verbatim clause from one of its
        `review_ids`; the other ids in the group carry a near-identical clause.
        """
        ordered = sorted(reviews, key=lambda r: getattr(r, "id", 0) or 0)
        total = len(ordered)

        # (aspect, polarity, signature) -> {review_id: [surface phrases]}
        groups: Dict[Tuple[str, str, Tuple[str, ...]], Dict[int, List[str]]] = defaultdict(
            lambda: defaultdict(list)
        )
        reviews_with_reasons = 0

        for review in ordered:
            review_id = getattr(review, "id", None)
            if review_id is None:
                continue
            text = getattr(review, "content", "") or ""
            produced = False
            for clause in self._clauses(text):
                aspects = self._aspects_in(clause)
                if not aspects:
                    continue
                display = self._display(clause)
                if not display:
                    continue
                signature = self._signature(display)
                # A clause made only of stopwords has no content signature; fall
                # back to its words so it stays distinct from every other group.
                key_text = signature if signature else tuple(display.lower().split())
                for aspect in aspects:
                    polarity = self._polarity(display, aspect)
                    groups[(aspect, polarity, key_text)][review_id].append(display)
                    produced = True
            if produced:
                reviews_with_reasons += 1

        merged = self._merge_contained(groups)
        return self._build_payload(merged, total, reviews_with_reasons)

    @staticmethod
    def _merge_contained(
        groups: Dict[Tuple[str, str, Tuple[str, ...]], Dict[int, List[str]]]
    ) -> Dict[Tuple[str, str, Tuple[str, ...]], Dict[int, List[str]]]:
        """
        Fold a group into a shorter same-polarity group when its content words
        are a superset of the shorter one's ("the price is high for what is an
        incremental update" -> "the price is high").

        Processing in ascending signature length makes the outcome independent
        of input order.
        """
        ordered_keys = sorted(
            groups.keys(), key=lambda k: (len(k[2]), k[2], k[0], k[1])
        )
        merged: Dict[Tuple[str, str, Tuple[str, ...]], Dict[int, List[str]]] = {}
        for key in ordered_keys:
            target = key
            key_words = set(key[2])
            for existing in merged:
                if existing[0] != key[0] or existing[1] != key[1]:
                    continue
                if set(existing[2]) <= key_words:
                    target = existing
                    break
            bucket = merged.setdefault(target, defaultdict(list))
            for review_id, phrases in groups[key].items():
                bucket[review_id].extend(phrases)
        return merged

    def _build_payload(
        self,
        merged: Dict[Tuple[str, str, Tuple[str, ...]], Dict[int, List[str]]],
        total: int,
        reviews_with_reasons: int,
    ) -> Dict[str, Any]:
        reasons_by_aspect: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for (aspect, polarity, _signature), by_review in merged.items():
            review_ids = sorted(by_review)
            # The shortest surface form is the most reusable wording; ties break
            # on the first review that used it, then on the text itself, so the
            # choice never depends on dictionary ordering.
            first_seen: Dict[str, int] = {}
            for review_id, phrases in by_review.items():
                for surface in phrases:
                    if surface not in first_seen or review_id < first_seen[surface]:
                        first_seen[surface] = review_id
            phrase = min(first_seen, key=lambda p: (len(p), first_seen[p], p))
            reasons_by_aspect[aspect].append({
                "phrase": phrase,
                "polarity": polarity,
                "mentions": len(review_ids),
                "review_ids": review_ids,
            })

        aspects: List[Dict[str, Any]] = []
        for aspect, reasons in reasons_by_aspect.items():
            reasons.sort(key=lambda r: (-r["mentions"], r["phrase"]))
            counts = {"positive": 0, "neutral": 0, "negative": 0}
            for reason in reasons:
                counts[reason["polarity"]] += 1
            total_reasons = len(reasons)
            score = round(
                (counts["positive"] + counts["neutral"] * 0.5) / total_reasons * 100.0, 1
            )
            if score >= 65.0:
                polarity = "positive"
            elif score <= 45.0:
                polarity = "negative"
            elif counts["positive"] and counts["negative"]:
                polarity = "mixed"
            else:
                polarity = "neutral"
            aspects.append({
                "aspect": ASPECT_LABELS.get(aspect, aspect.title()),
                "score": score,
                "mentions": len({rid for reason in reasons for rid in reason["review_ids"]}),
                "polarity": polarity,
                "reasons": reasons,
            })

        aspects.sort(key=lambda a: (-a["mentions"], a["aspect"]))

        problems: List[Dict[str, Any]] = []
        praise: List[Dict[str, Any]] = []
        for aspect in aspects:
            for reason in aspect["reasons"]:
                entry = {
                    "phrase": reason["phrase"],
                    "aspect": aspect["aspect"],
                    "polarity": reason["polarity"],
                    "mentions": reason["mentions"],
                    "review_ids": reason["review_ids"],
                }
                if reason["polarity"] == "negative":
                    problems.append(entry)
                elif reason["polarity"] == "positive":
                    praise.append(entry)

        problems.sort(key=lambda r: (-r["mentions"], r["phrase"], r["aspect"]))
        praise.sort(key=lambda r: (-r["mentions"], r["phrase"], r["aspect"]))

        return {
            "aspects": aspects,
            "recurring_problems": problems,
            "recurring_praise": praise,
            "coverage": {
                "reviews_analysed": total,
                "reviews_with_reasons": reviews_with_reasons,
            },
        }


review_mining_service = ReviewMiningService()
