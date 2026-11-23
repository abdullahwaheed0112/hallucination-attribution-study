"""Find the page of each figure used in the comparison table inside the PDFs of docs/papers (reads the PDFs as data only).
Usage: python -P -E scripts/check_comparison_sources.py <docs/papers folder> <out file>
"""
import pathlib, re, sys
import pypdf

NEEDLES = {
    "AgentHallu": ["41.1%", "693", "11.6%", "step localization"],
    "DiLLS": ["3.67", "2.25", "4.50", "3.42", "58%", "20%", "12 participants", "Wilcoxon"],
    "Effects of LLM-based Search": ["47%", "93%", "26%", "53%", "58%", "90 ", "120 "],
    "Fostering Appropriate Reliance": ["308", "78.2", "82.8", "68.2", "69.7", "83.3", "76.9"],
    "Seeing the Whole Elephant": ["33.3", "66.7", "220", "0.72", "0.64", "8%", "52%"],
    "Zhou et al.": ["85.2", "66.1", "H(3)", "13.12", "localiz"],
}
papers = pathlib.Path(sys.argv[1])
out = []
for key, needles in NEEDLES.items():
    f = next((p for p in papers.glob("*.pdf") if p.name.startswith(key)), None)
    if f is None:
        out.append("%s: PDF NOT FOUND" % key); continue
    r = pypdf.PdfReader(str(f))
    pages = [(i + 1, re.sub(r"\s+", " ", (p.extract_text() or ""))) for i, p in enumerate(r.pages)]
    out.append("== %s (%d pages) %s" % (key, len(pages), f.name))
    for n in needles:
        hits = [i for i, t in pages if n in t]
        out.append("   %-18s pages %s" % (n, hits[:12] if hits else "NOT FOUND"))
pathlib.Path(sys.argv[2]).write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
