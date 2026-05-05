"""Convert docs/MIGRATION.md to docs/MIGRATION.pdf."""
from pathlib import Path
import markdown
from xhtml2pdf import pisa

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "MIGRATION.md"
OUT = ROOT / "docs" / "MIGRATION.pdf"

CSS = """
@page { size: A4; margin: 2cm; }
body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; line-height: 1.4; color: #222; }
h1 { font-size: 20pt; color: #003366; border-bottom: 2px solid #003366; padding-bottom: 4px; }
h2 { font-size: 14pt; color: #003366; margin-top: 18pt; border-bottom: 1px solid #ccc; padding-bottom: 2px; }
h3 { font-size: 12pt; color: #004080; margin-top: 12pt; }
code { font-family: 'Consolas', monospace; background: #f4f4f4; padding: 1px 3px; border-radius: 2px; }
pre { background: #f4f4f4; padding: 8px; border-left: 3px solid #003366; font-family: 'Consolas', monospace; font-size: 9pt; white-space: pre-wrap; }
pre code { background: transparent; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0; }
th, td { border: 1px solid #999; padding: 4px 6px; text-align: left; vertical-align: top; }
th { background: #e8eef5; }
a { color: #0066cc; text-decoration: none; }
blockquote { border-left: 3px solid #ccc; padding-left: 10px; color: #555; }
ul, ol { padding-left: 22px; }
li { margin: 2px 0; }
hr { border: none; border-top: 1px solid #ccc; margin: 12pt 0; }
"""

md = SRC.read_text(encoding="utf-8")
html_body = markdown.markdown(
    md,
    extensions=["fenced_code", "tables", "toc", "sane_lists"],
)
html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{html_body}</body></html>"

with open(OUT, "wb") as f:
    result = pisa.CreatePDF(html, dest=f, encoding="utf-8")

if result.err:
    raise SystemExit(f"PDF generation failed: {result.err} errors")
print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")
