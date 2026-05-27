"""Unicode, zero-width, and homoglyph preprocessor normalization layer for LLM Guard."""

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
    """
    Remove formatting and invisible characters from the Unicode Cf category.
    
    This includes zero-width space (U+200B), zero-width non-joiner (U+200C),
    zero-width joiner (U+200D), word joiner (U+2060), and zero-width
    no-break space (U+FEFF).

    Args:
        text: Prompt string to filter.

    Returns:
        Filtered string without Cf category characters.
    """
    if not text:
        return ""
    return "".join(c for c in text if unicodedata.category(c) != "Cf")


def normalize_unicode(text: str) -> str:
    """
    Convert stylized Unicode font variations to standard Unicode equivalents using NFKC.
    
    This handles mathematical bold/italic, fullwidth, circle-enclosed, and script
    variations of alphanumeric characters.

    Args:
        text: Prompt string to normalize.

    Returns:
        Canonical NFKC normalized string.
    """
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text)


def canonicalize_homoglyphs(text: str) -> str:
    """
    Replace lookalike Cyrillic and Greek characters with standard ASCII equivalents.

    Args:
        text: Normalized prompt string.

    Returns:
        Canonical string with Latin counterparts substituted.
    """
    if not text:
        return ""
    return "".join(HOMOGLYPH_MAPPING.get(c, c) for c in text)


def normalize_prompt(text: str) -> str:
    """
    Clean and canonicalize prompt using the full normalization pipeline.
    
    Executes in sequence:
    1. Zero-width/format characters stripped
    2. Unicode compatibility normalization (NFKC)
    3. Cyrillic/Greek homoglyph substitutions canonicalized

    Args:
        text: Raw input prompt string.

    Returns:
        Cleaned and normalized prompt.
    """
    if not text:
        return ""
    text = remove_zero_width_chars(text)
    text = normalize_unicode(text)
    text = canonicalize_homoglyphs(text)
    return text
