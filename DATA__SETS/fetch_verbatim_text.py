#!/usr/bin/env python3
"""
fetch_verbatim_text.py
-----------------------
Pulls the verbatim "Policy" section text directly from each Aetna CPB page
listed in aetna_rag_chunks.jsonl (source_reference.url) and writes it into a
new "verbatim_text" field per chunk (deduplicated by URL, so each page is
fetched once even though a policy may contribute multiple chunks).

Why this script exists instead of the text already being in the JSONL:
Anthropic's Claude is not permitted to reproduce extended copyrighted web
content in its own output (see Aetna's copyright notice on every CPB page).
Running this script on YOUR OWN infrastructure, against Aetna's public site,
is a normal web-scraping operation you control and are responsible for --
review Aetna's Terms of Use before scraping at any volume, and keep the
source_url + fetch timestamp with whatever text you store so the provenance
is auditable.

Usage:
    pip install requests beautifulsoup4
    python3 fetch_verbatim_text.py aetna_rag_chunks.jsonl aetna_rag_chunks.verbatim.jsonl

Notes:
- This grabs the whole "Policy" section (Scope of Policy through end of the
  numbered policy items, stopping before "Applicable CPT / HCPCS / ICD-10
  Codes"). It does not attempt to isolate the exact sub-item that matches a
  single criterion_id -- for that level of precision, a human reviewer should
  trim the fetched section down to the relevant sub-item and set
  text_status to "verbatim" once confirmed.
- Aetna's CPB pages change over time (see revision_date / next_review_date
  in Policy_Master). Re-run this periodically and diff against what's stored.
"""
import json
import sys
import time
import re

def fetch_policy_section(url, session):
    import requests
    from bs4 import BeautifulSoup

    resp = session.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # The CPB page structure places policy text between the "Policy" H2/H3
    # anchor and the "Applicable CPT / HCPCS / ICD-10 Codes" heading.
    text_parts = []
    capture = False
    for el in soup.find_all(["h1", "h2", "h3", "p", "li", "table"]):
        heading_text = el.get_text(" ", strip=True) if el.name in ("h1", "h2", "h3") else ""
        if el.name in ("h1", "h2", "h3"):
            if re.match(r"^Policy$", heading_text, re.I):
                capture = True
                continue
            if re.search(r"Applicable CPT|Background|References", heading_text, re.I):
                capture = False
        if capture:
            txt = el.get_text(" ", strip=True)
            if txt:
                text_parts.append(txt)

    return "\n".join(text_parts).strip()


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} input.jsonl output.jsonl")
        sys.exit(1)

    in_path, out_path = sys.argv[1], sys.argv[2]

    import requests
    session = requests.Session()

    rows = []
    with open(in_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    cache = {}
    for row in rows:
        url = row.get("source_reference", {}).get("url")
        if not url:
            continue
        if url not in cache:
            print(f"Fetching {url} ...")
            try:
                cache[url] = fetch_policy_section(url, session)
            except Exception as e:
                print(f"  FAILED: {e}")
                cache[url] = None
            time.sleep(1)  # be polite
        row["verbatim_text"] = cache[url]
        row["verbatim_fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with open(out_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
