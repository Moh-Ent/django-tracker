"""Template safety check. Run from the project root:
    python tools/check_templates.py

1. Every <form method="post"> must contain {% csrf_token %}.
2. {% if %}, {% for %}, {% block %} and {% with %} must be closed.
Exits with an error if anything is wrong. Needs no Django."""
import re
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
PAIRS = [("if", "endif"), ("for", "endfor"), ("block", "endblock"), ("with", "endwith")]
FORM = re.compile(r"<form\b([^>]*)>(.*?)</form>", re.DOTALL | re.IGNORECASE)
POST = re.compile(r"""method\s*=\s*["']post["']""", re.IGNORECASE)

problems = []
files = sorted(TEMPLATES.rglob("*.html"))
post_forms = 0

for f in files:
    text = f.read_text(encoding="utf-8")
    name = f.relative_to(TEMPLATES)

    for attrs, body in FORM.findall(text):
        if POST.search(attrs):
            post_forms += 1
            if "{% csrf_token %}" not in body:
                problems.append(f"{name}: a POST form is missing {{% csrf_token %}}")

    for opening, closing in PAIRS:
        n_open = len(re.findall(r"\{%\s*" + opening + r"\b", text))
        n_close = len(re.findall(r"\{%\s*" + closing + r"\b", text))
        if n_open != n_close:
            problems.append(f"{name}: {opening} x{n_open} but {closing} x{n_close}")

print(f"Checked {len(files)} templates and {post_forms} POST forms.")
if problems:
    print("PROBLEMS:")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("All good: every POST form has a csrf_token and all tags are closed.")
