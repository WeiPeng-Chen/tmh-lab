"""列出 OpenAlex 上有、但網站（build.py 的 PUBS）還沒有的論文，供人工確認。

用法：python check_new_papers.py        （加 --all 會連預印本一起列出）
- 不會修改網站；結果只印在畫面上，並存成 new_papers.txt。
- 確認是老師的論文後，把它加進 build.py 的 PUBS，再執行 python build.py。
- 不是老師的論文（資料庫誤配），把它的 DOI 或標題關鍵字寫進 ignore.txt（一行一筆）。
"""
import ast, json, os, re, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
ORCID = "https://orcid.org/0000-0001-6350-3180"   # 已與陽明交大學術資料庫核對
NAME = "hu"                                        # 作者姓 (小寫)，用來標示老師在作者列表中的位置


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def site_papers():
    """從 build.py 讀出 PUBS 與 DOIS，不必執行整個網站產生程式。"""
    tree = ast.parse(open(os.path.join(ROOT, "build.py"), encoding="utf-8").read())
    got = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ("PUBS", "DOIS"):
            got[node.targets[0].id] = ast.literal_eval(node.value)
    titles = {norm(p[1]) for p in got["PUBS"]}
    dois = {d.lower() for d in got["DOIS"].values()}
    dois |= {p[4][4:].lower() for p in got["PUBS"] if p[4].startswith("doi:")}
    return titles, dois


def ignored():
    f = os.path.join(ROOT, "ignore.txt")
    return [l.strip().lower() for l in open(f, encoding="utf-8")] if os.path.exists(f) else []


def fetch():
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode({
        "filter": f"author.orcid:{ORCID}", "per-page": 200, "sort": "publication_date:desc",
        "select": "title,publication_year,publication_date,doi,type,authorships,primary_location",
        "mailto": "ss9711997@gmail.com"})
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)["results"]


def main():
    titles, dois = site_papers()
    skip = ignored()
    out = []
    for w in fetch():
        doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
        title = w.get("title") or ""
        if (doi and doi in dois) or norm(title) in titles:
            continue
        if any(k and (k in doi or k in title.lower()) for k in skip):
            continue
        if w.get("type") in ("preprint", "peer-review") and "--all" not in sys.argv:
            continue   # 預印本與審查回覆通常和已收錄的正式版重複；加 --all 可一併列出
        authors = [a["author"]["display_name"] for a in w.get("authorships", [])]
        src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or "(無期刊資訊)"
        flag = ""
        if not any(NAME in a.lower().split()[-1] for a in authors if a):
            flag = "  ⚠ 作者列表裡找不到姓 Hu，可能是誤配"
        if w.get("type") in ("preprint", "peer-review", "letter", "paratext"):
            flag += f"  [類型：{w['type']}]"
        out.append(f"{w.get('publication_date','?')}  {title}\n    {', '.join(authors[:12])}{' …' if len(authors) > 12 else ''}\n"
                   f"    {src}   doi:{doi or '—'}{flag}\n")
    text = f"網站尚未收錄的論文：{len(out)} 筆\n\n" + "\n".join(out)
    open(os.path.join(ROOT, "new_papers.txt"), "w", encoding="utf-8").write(text)
    print(text)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
