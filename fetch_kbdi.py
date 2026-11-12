"""Copy the Florida Forest Service county KBDI table into data/kbdi.json.

FDACS doesn't allow web pages on other sites to read its report, so this runs
in GitHub Actions and saves the numbers next to the burn outlook page.
"""
import datetime
import html
import json
import os
import re
import sys
import urllib.request

URL = "https://weather.fdacs.gov/KBDI/report/kbdi_current.html"
COUNTY = "Brevard"
OUT = os.path.join("data", "kbdi.json")


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def as_int(s):
    s = (s or "").strip()
    return int(s) if re.fullmatch(r"-?\d+", s) else None


def parse(raw):
    m = re.search(r"KBDI\s+Summary\s+for\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", clean(raw))
    date = datetime.datetime.strptime(re.sub(r"\s+", " ", m.group(1)), "%B %d, %Y").date().isoformat() if m else None
    rows = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", raw, re.S | re.I):
        cells = [clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
        if len(cells) < 4 or as_int(cells[1]) is None:
            continue   # header rows
        lo, _, hi = cells[3].partition("/")
        rows[cells[0]] = {"kbdi": as_int(cells[1]), "change": as_int(cells[2]), "min": as_int(lo), "max": as_int(hi)}
    return date, rows


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "ERPlanningForecast burn outlook (GitHub Actions)"})
    raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    date, rows = parse(raw)
    if COUNTY not in rows or not date:
        sys.exit(f"{COUNTY} row or report date not found; the FDACS page layout may have changed")
    out = {"source": URL, "date": date, "county": COUNTY, **rows[COUNTY], "counties": rows,
           "fetched": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()}
    try:
        with open(OUT) as f:
            old = json.load(f)
        if old.get("date") == date and old.get("counties") == rows:
            print(f"No change: {COUNTY} KBDI {rows[COUNTY]['kbdi']} for {date}")
            return
    except (OSError, ValueError):
        pass
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print(f"Saved {COUNTY} KBDI {rows[COUNTY]['kbdi']} for {date}")


if __name__ == "__main__":
    main()
