"""Normalize text before guard classification.

The guard pipeline needs a predictable prompt representation before the
classifier or heuristic filters make a decision. This module strips
formatting-only characters, applies Unicode compatibility normalization,
and canonicalizes a handful of common Cyrillic and Greek homoglyphs back to
their Latin equivalents so downstream matching sees the same text a human
would expect.
"""

import unicodedata
from typing import Dict

# Map lookalike Cyrillic and Greek characters to standard Latin ASCII equivalents
HOMOGLYPH_MAPPING: Dict[str, str] = {
    # Cyrillic lookalikes
    "\u0410": "A",  # А (Capital A)
    "\u0430": "a",  # а (Small a)
    "\u0412": "B",  # В (Capital Ve)
    "\u0421": "C",  # С (Capital Es)
    "\u0441": "c",  # с (Small es)
    "\u0415": "E",  # Е (Capital Ie)
    "\u0435": "e",  # е (Small ie)
    "\u041d": "H",  # Н (Capital En)
    "\u0406": "I",  # І (Capital Byelorussian-Ukrainian i)
    "\u0456": "i",  # і (Small byelorussian-ukrainian i)
    "\u0408": "J",  # Ј (Capital J)
    "\u0458": "j",  # ј (Small j)
    "\u041a": "K",  # К (Capital Ka)
    "\u043a": "k",  # к (Small ka)
    "\u041c": "M",  # М (Capital Em)
    "\u041e": "O",  # О (Capital O)
    "\u043e": "o",  # о (Small o)
    "\u0420": "P",  # Р (Capital Er)
    "\u0440": "p",  # р (Small er)
    "\u0422": "T",  # Т (Capital Te)
    "\u0425": "X",  # Х (Capital Ha)
    "\u0445": "x",  # х (Small ha)
    "\u0423": "Y",  # У (Capital U)
    "\u0443": "y",  # у (Small u)
    "\u0405": "S",  # Ѕ (Capital Dze)
    "\u0455": "s",  # ѕ (Small dze)
    
    # Greek lookalikes
    "\u0391": "A",  # Α (Capital Alpha)
    "\u03b1": "a",  # α (Small Alpha)
    "\u0392": "B",  # Β (Capital Beta)
    "\u0395": "E",  # Ε (Capital Epsilon)
    "\u0396": "Z",  # Ζ (Capital Zeta)
    "\u0397": "H",  # Η (Capital Eta)
    "\u0399": "I",  # Ι (Capital Iota)
    "\u03b9": "i",  # ι (Small Iota)
    "\u039a": "K",  # Κ (Capital Kappa)
    "\u03ba": "k",  # κ (Small Kappa)
    "\u039c": "M",  # Μ (Capital Mu)
    "\u039d": "N",  # Ν (Capital Nu)
    "\u039f": "O",  # Ο (Capital Omicron)
    "\u03bf": "o",  # ο (Small Omicron)
    "\u03a1": "P",  # Ρ (Capital Rho)
    "\u03a4": "T",  # Τ (Capital Tau)
    "\u03c4": "t",  # τ (Small Tau)
    "\u03a5": "Y",  # Υ (Capital Upsilon)
    "\u03a7": "X",  # Χ (Capital Chi)
    "\u03c7": "x",  # χ (Small Chi)
}


def remove_zero_width_chars(text: str) -> str:
    """Strip invisible Unicode format characters from ``text``."""
    if not text:
        return ""
    return "".join(c for c in text if unicodedata.category(c) != "Cf")


def normalize_unicode(text: str) -> str:
    """Apply NFKC normalization to collapse compatibility variants."""
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text)


def canonicalize_homoglyphs(text: str) -> str:
    """Map common Greek and Cyrillic lookalikes to Latin ASCII forms."""
    if not text:
        return ""
    return "".join(HOMOGLYPH_MAPPING.get(c, c) for c in text)


def normalize_prompt(text: str) -> str:
    """Run the full normalization pipeline used by the guard stack."""
    if not text:
        return ""
    text = remove_zero_width_chars(text)
    text = normalize_unicode(text)
    text = canonicalize_homoglyphs(text)
    return text
