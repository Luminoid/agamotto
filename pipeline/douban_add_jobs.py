"""Append Douban jobs for titles not yet in douban_jobs.json (films with a Wikidata Douban id -> subject pages,
everything else -> mobile search), so douban_subj.mjs and douban_m.mjs pick up only the new keys."""
import json, os
from enrich import norm

HERE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(HERE, "data.json")))
jobs = json.load(open(os.path.join(HERE, "douban_jobs.json")))
split = json.load(open(os.path.join(HERE, "douban_split.json")))
have = {j["key"] for j in jobs}
added = []
for t in data["titles"]:
    if t["key"] in have:
        continue
    jobs.append(dict(key=t["key"], kind=t["kind"], year=int(t["date"][:4]) if t.get("date") else None,
                     names=[norm(t["en"])], en=t["en"], zh=t["zh"], wd=t["douban"]))
    (split["subject"] if t["kind"] != "series" and t["douban"] else split["search"]).append(t["key"])
    added.append(t["key"])
json.dump(jobs, open(os.path.join(HERE, "douban_jobs.json"), "w"), ensure_ascii=False, indent=1)
json.dump(split, open(os.path.join(HERE, "douban_split.json"), "w"), ensure_ascii=False, indent=1)
print(len(added), "added;", sum(1 for k in added if k in split["subject"]), "subject,", sum(1 for k in added if k in split["search"]), "search")
