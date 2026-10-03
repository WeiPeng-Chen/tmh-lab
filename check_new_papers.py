"""列出 OpenAlex 上有、但網站（build.py 的 PUBS）還沒有的論文，供人工確認；也可以回頭檢查網站已有的論文。

用法：
  python check_new_papers.py            找新論文（加 --all 會連預印本一起列出）
  python check_new_papers.py --audit    逐篇用 Crossref 核對網站上每篇論文的作者列表，找出作者其實不是胡德民的誤收

- 不會修改網站；結果只印在畫面上，新論文清單另存成 new_papers.txt。
- 確認是老師的論文後，把它加進 build.py 的 PUBS，再執行 python build.py。
- 不是老師的論文（資料庫誤配），把它的 DOI 或標題關鍵字寫進 ignore.txt（一行一筆）。

為什麼要比對全名：資料庫的作者歸戶（ORCID／OpenAlex）會把同姓「Hu」的人誤併進來，
只檢查姓氏會漏掉（例如 Imperial College 的 Tinghao Hu）。所以這裡一律要求作者列表中
出現「Teh-Min Hu」或 T.-M. Hu / TM Hu 這幾種寫法才算數，沒有的一律標示為疑似誤配。
"""
import ast, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
ORCID = "https://orcid.org/0000-0001-6350-3180"   # 已與陽明交大學術資料庫核對
MAILTO = "ss9711997@gmail.com"
PI_FORMS = {"tehminhu", "tmhu", "hutehmin", "hutm"}


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def is_pi(name):
    """作者姓名是否為 Teh-Min Hu（允許連字號、點、全形連字號與姓名顛倒的寫法）。"""
    return re.sub(r"[^a-z]", "", (name or "").lower()) in PI_FORMS


def hu_authors(names):
    return [n for n in names if n and re.search(r"\bhu\b", n.lower())]


def site_papers():
    """從 build.py 讀出 PUBS 與 DOIS，不必執行整個網站產生程式。回傳 (標題集合, DOI 集合, [(標題, DOI)])。"""
    tree = ast.parse(open(os.path.join(ROOT, "build.py"), encoding="utf-8").read())
    got = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ("PUBS", "DOIS"):
            got[node.targets[0].id] = ast.literal_eval(node.value)
    pairs = []
    for p in got["PUBS"]:
        d = p[4][4:] if p[4] and p[4].startswith("doi:") else next((v for k, v in got["DOIS"].items() if p[1].startswith(k)), None)
        pairs.append((p[1], d))
    titles = {norm(t) for t, _ in pairs}
    dois = {d.lower() for _, d in pairs if d}
    return titles, dois, pairs


def ignored():
    f = os.path.join(ROOT, "ignore.txt")
    return [l.strip().lower() for l in open(f, encoding="utf-8") if l.strip()] if os.path.exists(f) else []


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": f"tmh-lab-check (mailto:{MAILTO})"}), timeout=60) as r:
        return json.load(r)


def fetch():
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode({
        "filter": f"author.orcid:{ORCID}", "per-page": 200, "sort": "publication_date:desc",
        "select": "title,publication_year,publication_date,doi,type,authorships,primary_location", "mailto": MAILTO})
    return get_json(url)["results"]


def find_new():
    titles, dois, _ = site_papers()
    skip = ignored()
    ok, suspicious = [], []
    for w in fetch():
        doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
        title = w.get("title") or ""
        if (doi and doi in dois) or norm(title) in titles:
            continue
        if any(k and (k in doi or k in title.lower()) for k in skip):
            continue
        if w.get("type") in ("preprint", "peer-review") and "--all" not in sys.argv:
            continue
        authors = [a["author"]["display_name"] for a in w.get("authorships", [])]
        src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or "(無期刊資訊)"
        flag = f"  [類型：{w['type']}]" if w.get("type") in ("preprint", "peer-review", "letter", "paratext") else ""
        entry = (f"{w.get('publication_date','?')}  {title}\n    {', '.join(authors[:12])}{' …' if len(authors) > 12 else ''}\n"
                 f"    {src}   doi:{doi or '—'}{flag}\n")
        if any(is_pi(a) for a in authors):
            ok.append(entry)
        else:
            others = hu_authors(authors)
            suspicious.append(entry + f"    ⚠ 作者列表裡沒有 Teh-Min Hu；姓 Hu 的作者：{', '.join(others) or '無'}。疑似同姓他人，請勿收錄。\n")
    text = f"網站尚未收錄、且作者列表有 Teh-Min Hu 的論文：{len(ok)} 筆\n\n" + "\n".join(ok)
    if suspicious:
        text += f"\n--- 疑似誤配（作者列表沒有 Teh-Min Hu）：{len(suspicious)} 筆 ---\n\n" + "\n".join(suspicious)
    open(os.path.join(ROOT, "new_papers.txt"), "w", encoding="utf-8").write(text)
    print(text)


def crossref_authors(doi):
    m = get_json("https://api.crossref.org/works/" + urllib.parse.quote(doi) + f"?mailto={MAILTO}")["message"]
    return [f"{a.get('given', '')} {a.get('family', a.get('name', ''))}".strip() for a in m.get("author", [])]


def audit():
    _, _, pairs = site_papers()
    bad, nodoi, unknown = [], [], []
    for title, doi in pairs:
        if not doi:
            nodoi.append(title)
            continue
        try:
            names = crossref_authors(doi)
        except Exception as e:
            unknown.append((title, doi, str(e)))
            continue
        if not any(is_pi(n) for n in names):
            bad.append((title, doi, hu_authors(names), names))
        time.sleep(0.3)
    print(f"已核對 {len(pairs) - len(nodoi) - len(unknown)} 篇有 DOI 的論文。")
    if bad:
        print(f"\n⚠ 作者列表裡沒有 Teh-Min Hu 的論文：{len(bad)} 篇")
        for t, d, hu, names in bad:
            print(f"  - {t}\n    doi:{d}\n    姓 Hu 的作者：{', '.join(hu) or '無'}\n    全部作者：{', '.join(names)}")
    else:
        print("所有有 DOI 的論文，作者列表都有 Teh-Min Hu。")
    if unknown:
        print(f"\n（Crossref 查不到，需人工確認：{len(unknown)} 篇）")
        for t, d, e in unknown:
            print(f"  - {t}  doi:{d}  ({e})")
    print(f"\n（沒有 DOI、未核對：{len(nodoi)} 篇，多為 2001 年以前或研討會摘要）")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    audit() if "--audit" in sys.argv else find_new()
