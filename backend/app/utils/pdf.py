"""PDF rendering for reports (T32) — WeasyPrint, no headless browser."""

from __future__ import annotations

import markdown

_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: sans-serif; color: #e5e7eb; background: #0b0f14;
         padding: 32px; }}
  h1 {{ color: #f59e0b; }}
  h2, h3 {{ color: #93c5fd; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th, td {{ border: 1px solid #374151; padding: 8px; text-align: left; }}
  th {{ background: #1f2937; }}
  code, pre {{ background: #1f2937; padding: 2px 4px; border-radius: 4px; }}
</style>
</head>
<body>
<h1>{title}</h1>
{body}
</body>
</html>
"""


def render_report_pdf(markdown_text: str, title: str) -> bytes:
    """Convert markdown to a dark-styled PDF and return the bytes."""
    body_html = markdown.markdown(markdown_text, extensions=["tables", "fenced_code"])
    html = _TEMPLATE.format(title=_html_escape(title), body=body_html)

    from weasyprint import HTML

    pdf_bytes = HTML(string=html).write_pdf()
    return bytes(pdf_bytes)


def _html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
