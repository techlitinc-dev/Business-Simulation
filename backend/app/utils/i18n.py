"""Report localization — language instruction + currency formatting.

DeepSeek handles translation natively: we pass the target language into the
section-writer prompt rather than translating on the client side.
"""

from __future__ import annotations

SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "zh": "Simplified Chinese",
    "ja": "Japanese",
}

CURRENCY_FORMATS = {
    "USD": "${:,.0f}",
    "EUR": "€{:,.0f}",
    "GBP": "£{:,.0f}",
    "BRL": "R${:,.0f}",
    "JPY": "¥{:,.0f}",
}


def get_language_instruction(lang_code: str) -> str:
    """Return a prompt suffix instructing the LLM to write in ``lang_code``.

    Empty for English (the default) so existing prompts are unchanged.
    """
    name = SUPPORTED_LANGUAGES.get(lang_code, "English")
    if lang_code == "en":
        return ""
    return (
        f"\n\nIMPORTANT: Write your response in {name}. "
        f"All narrative text must be in {name}."
    )


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format an amount with the currency's symbol (defaults to USD)."""
    fmt = CURRENCY_FORMATS.get(currency, "${:,.0f}")
    return fmt.format(amount)
