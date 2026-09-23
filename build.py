"""Static site generator: python build.py  ->  writes every page from NAV + page() calls."""
import os, re, html, base64, hashlib, secrets, sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = "TMH Laboratory"
PI = "Teh-Min Hu"

# ---- Members (locked) area -------------------------------------------------------
# The password is NOT stored in the site. build.py reads it from the environment
# (MEMBERS_PASSWORD) or from ../members-password.txt (outside the published folder).
def _password():
    if os.environ.get("MEMBERS_PASSWORD"):
        return os.environ["MEMBERS_PASSWORD"]
    f = os.path.join(ROOT, "..", "members-password.txt")
    if os.path.exists(f):
        return open(f, encoding="utf-8").read().strip()
    sys.exit("找不到密碼：請建立 ../members-password.txt 或設定 MEMBERS_PASSWORD")


PBKDF2_ITER = 200_000


def encrypt(plaintext):
    """AES-256-GCM, key = PBKDF2-SHA256(password, salt, 200k). Payload = base64(salt|iv|ciphertext)."""
    salt, iv = secrets.token_bytes(16), secrets.token_bytes(12)
    key = hashlib.pbkdf2_hmac("sha256", _password().encode(), salt, PBKDF2_ITER, dklen=32)
    ct = AESGCM(key).encrypt(iv, plaintext.encode("utf-8"), None)
    return base64.b64encode(salt + iv + ct).decode()

# ---- Information architecture (single source for sidebar + pages) ----------
NAV = [
    {"id": "home", "label": "首頁", "href": "index.html"},
    {"id": "research", "label": "研究", "children": [
        ("研究領域", "research/areas.html"),
        ("技術與專利", "research/technologies.html")]},
    {"id": "publications", "label": "發表論文", "href": "publications.html"},
    {"id": "people", "label": "人員", "children": [
        ("主持人", "people/principal-investigator.html"),
        ("成員", "people/members.html")]},
    {"id": "news", "label": "最新消息", "href": "news.html"},
    {"id": "resources", "label": "相關連結", "href": "resources/useful-links.html"},
]

MEMBERS = {"id": "members", "label": "成員專區", "children": [
    ("儀器設備", "members/instruments.html"),
    ("軟體與工具", "members/software-tools.html"),
    ("公用文件", "members/shared-documents.html")]}

LOCK = '<svg class="lock" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="7" width="10" height="7" rx="1.5"/><path d="M5 7V5a3 3 0 016 0v2"/></svg>'

CHEV = '<svg class="chev" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 3l5 5-5 5"/></svg>'
BURGER = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>'
AC = ' aria-current="page"'


def sidebar(cur, root):
    def group(g, private=False):
        kids = g["children"]
        is_cur = any(h == cur for _, h in kids)
        gid = "sub-" + g["id"]
        links = "".join(f'<a href="{root}{h}"{AC if h == cur else ""}>{html.escape(l)}</a>' for l, h in kids)
        return (f'<li class="nav-item"><button class="nav-toggle{" has-current" if is_cur else ""}" aria-expanded="{"true" if is_cur else "false"}" aria-controls="{gid}">'
                f'{LOCK if private else ""}<span>{g["label"]}</span>{CHEV}</button>'
                f'<div class="sub" id="{gid}"{"" if is_cur else " hidden"}>{links}</div></li>')

    items = ""
    for n in NAV:
        if "children" in n:
            items += group(n)
        else:
            items += f'<li class="nav-item"><a href="{root}{n["href"]}"{AC if n["href"] == cur else ""}>{n["label"]}</a></li>'
    return (f'<nav class="sidebar" id="sidebar" aria-label="主選單">'
            f'<a class="brand" href="{root}index.html"><img src="{root}assets/logo-mark.png" alt="" width="48">'
            f'<span class="brand-name">TMH Laboratory<small>藥物遞送研究室</small></span></a>'
            f'<div class="nav"><ul>{items}</ul>'
            f'<div class="members-wrap"><hr><ul class="members">{group(MEMBERS, True)}</ul></div>'
            f'<div class="affil"><hr><div class="logos"><img class="l-nycu" src="{root}assets/nycu.png" alt="國立陽明交通大學">'
            f'<img class="l-ph" src="{root}assets/pharmacy.png" alt="藥學系系徽"></div>'
            f'<p>國立陽明交通大學<br>藥學系</p></div></div></nav>')


def page(path, section, title, lede, body, top=None, member=False, nav_cur=None):
    """top: replaces the default title/lede block (used by the profile page)."""
    root = "../" * path.count("/")
    head = top if top else (f'<p class="eyebrow">{html.escape(section)}</p><h1>{html.escape(title)}</h1>'
                            + (f'<p class="lede">{lede}</p>' if lede else ""))
    if member:
        body = (f'<div id="gate" class="gate" data-payload="{encrypt(body)}">'
                f'<form id="gate-form">{LOCK}<label for="gate-pw">此區僅供實驗室成員使用，請輸入密碼。</label>'
                f'<div class="gate-row"><input id="gate-pw" type="password" autocomplete="off" required>'
                f'<button class="btn" type="submit">解鎖</button></div><p id="gate-msg" class="small" role="alert"></p></form>'
                f'<noscript><p>需要開啟 JavaScript 才能解鎖此頁。</p></noscript></div>')
    doc = f'''<!doctype html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title) if title == SITE else html.escape(title) + " · " + SITE}</title>
{'<meta name="robots" content="noindex">' if member else ""}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Noto+Sans+TC:wght@400;500;700&display=swap">
<link rel="stylesheet" href="{root}assets/site.css">
</head>
<body>
<a class="skip" href="#main">跳到主要內容</a>
<button class="menu-btn" aria-expanded="false" aria-controls="sidebar">{BURGER}<span>TMH Laboratory</span></button>
{sidebar(nav_cur or path, root)}
<div class="main">
<main class="page" id="main">
{head}
{body}
</main>
<footer class="footer"><span>© 2026 {SITE} · 國立陽明交通大學 藥學系</span><span><a href="{root}people/principal-investigator.html#contact">聯絡我們</a></span></footer>
</div>
<script src="{root}assets/site.js"></script>
</body>
</html>
'''
    out = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)


PH = '<span class="tag ph">待補充</span>'


def entries(rows, wide=False, lead=True):
    """rows: (meta, title, text) -> ruled list; lead=False drops the metadata column."""
    cls = "list" + (" wide" if wide else "") + ("" if lead else " nolead")
    return f'<ul class="{cls}">' + "".join(
        (f'<li><span class="meta">{m}</span>' if lead else "<li>") +
        f'<div><h3>{t}</h3>{f"<p class=muted>{d}</p>" if d else ""}</div></li>' for m, t, d in rows) + "</ul>"


def grid(rows):
    return '<div class="grid3">' + "".join(f'<div><h3>{t}</h3><p class="muted">{d}</p></div>' for t, d in rows) + "</div>"


def me(s):
    return s.replace(PI, f"<strong>{PI}</strong>").replace("TM Hu", "<strong>TM Hu</strong>")


def empty(text):
    return f'<div class="placeholder"><p>{text} {PH}</p></div>'


def photo(items, date, caption, root=""):
    """items: [(src, alt), ...], one or several photos from the same event, one caption."""
    imgs = "".join(f'<img src="{root}{src}" alt="{alt}" loading="lazy">' for src, alt in items)
    return (f'<figure class="event" data-n="{len(items)}"><div class="event-photos">{imgs}</div>'
            f'<figcaption><span class="meta">{date}</span> {caption}</figcaption></figure>')


def video(vid, title, credit):
    # A clickable thumbnail linking out to YouTube, not a live <iframe> embed: this page is opened as a local
    # file (file://) before the site has real hosting, and YouTube's embed player errors (e.g. "Error 153")
    # under a file:// origin. A thumbnail+link works everywhere, including once the site is properly hosted.
    return (f'<figure class="video"><a class="frame" href="https://youtu.be/{vid}" target="_blank" rel="noopener">'
            f'<img src="https://img.youtube.com/vi/{vid}/hqdefault.jpg" alt="{title}" loading="lazy">'
            f'<span class="play" aria-hidden="true"></span></a>'
            f'<figcaption><strong>{title}</strong><br><span class="muted small">{credit} · <a href="https://youtu.be/{vid}" target="_blank" rel="noopener">在 YouTube 觀看</a></span></figcaption></figure>')




# ---- Data (from Prof. Hu's CV, last updated 2022-08) ------------------------------
EDU = [("1997–2002", "藥劑學 博士", "美國俄亥俄州立大學"),
       ("1991–1993", "藥學 碩士", "國防醫學院 藥學研究所"),
       ("1985–1989", "藥學 學士", "國防醫學院 藥學系")]
POS = [("2025–2026", "訪問教授（Visiting Professor）", "奧克蘭大學藥學院（School of Pharmacy, University of Auckland），紐西蘭；接待教授：Darren Svirskis 教授；2025 年 7 月至 2026 年 7 月"),
       ("2020–迄今", "教授（2022 年 8 月至 2025 年兼任系主任）", "國立陽明交通大學 藥學系"),
       ("2016–迄今", "合聘教師", "國立陽明交通大學 藥理學研究所"),
       ("2016–2020", "副教授", "國立陽明大學 藥學系；2016–2020 合聘於生物藥學研究所"),
       ("2011–2016", "副教授", "國防醫學院 藥學系；2016–2019 兼任教師"),
       ("2002–2011", "助理教授", "國防醫學院 藥學系"),
       ("1989–1997", "助教", "國防醫學院 藥學系（1989–1991、1993–1997）")]
SERVICE = [("2021–2024", "董事", "財團法人醫藥工業技術發展中心"),
           ("2020–2022", "秘書長", "台灣藥學會"),
           ("2019–2024", "委員", "衛生福利部 中華藥典編修諮議會與諮詢會、藥品諮議小組、藥物食品分析期刊編輯小組"),
           ("2018–2021", "藥物小組委員", "衛生福利部 罕見疾病及藥物審議會"),
           ("2013–迄今", "審查委員", "科技部（現國家科學及技術委員會）生命科學研究發展司 專題研究計畫"),
           ("2005–迄今", "委員", "考選部 藥師國家考試")]

# (year, title, authors, venue, note)
PUBS = [
    ("2026", "Nitric oxide-releasing nanoparticles for retinal protection against blue light-induced oxidative and vascular injury",
     "George Hsiao, Hung-Chang Chou, Shih-Jiuan Chiu, Yen-Ju Chan, Tai-Ju Hsu, Yu-Yen Chen, Jaw-Jou Kang, Teh-Min Hu, Yu-Wen Cheng", "ACS Applied Nano Materials", "doi:10.1021/acsanm.6c02509"),
    ("2026", "Solvent-mediated organocatalytic browning of biogenic indoles enables the formation of zwitterionic nanoparticles",
     "Teh-Min Hu, Hsin-Hui Lin, Chun-Yi Huang, Mei-Hsiang Lin, Shih-Jiuan Chiu", "RSC Advances 16(15): 13114–13123", "doi:10.1039/d5ra09863g"),
    ("2026", "Structurally modified lysozyme via solvent browning: toward functional protein-based antioxidants",
     "Chih-Jung Chang, Ming-Chia Li, Teh-Min Hu", "International Journal of Biological Macromolecules, 150425", "doi:10.1016/j.ijbiomac.2026.150425"),
    ("2025", "Browned phenylalanine nanoparticles: controllable synthesis and nonmonotonic colloidal stability",
     "Teh-Min Hu, Wan-Yun Lin", "Colloids and Surfaces A: Physicochemical and Engineering Aspects, 139015", "doi:10.1016/j.colsurfa.2025.139015"),
    ("2025", "Albumin-based cryogels as floating platforms for gastroretentive drug delivery applications",
     "Wei-Chin Hsu, Teh-Min Hu", "ACS Omega 10(33): 37639", "doi:10.1021/acsomega.5c04153"),
    ("2025", "Autonomous devices for drug delivery",
     "Abdulkadir Sanli, Teh-Min Hu, Leyang Li, Firat Güder", "Nature Biomedical Engineering 9(8): 1182–1183", "doi:10.1038/s41551-025-01473-x"),
    ("2024", "A nano-platform harnessing synergistic amino acid browning for biomedical applications",
     "Teh-Min Hu, Jia-An Liang, Yi-Hua Chiang", "Journal of Materials Chemistry B 12(26): 6410–6423", "doi:10.1039/d4tb00529e"),
    ("2024", "Quantitative analysis of macrophage uptake and retention of fluorescent organosilica nanoparticles: implications for nanoparticle delivery and therapeutics",
     "Hung-Chang Chou, Shih-Jiuan Chiu, Teh-Min Hu", "ACS Applied Nano Materials 7(4): 3656–3667", "doi:10.1021/acsanm.3c05058"),
    ("2023", "Chemical reactivity of the tryptophan/acetone/DMSO triad system and its potential applications in nanomaterial synthesis",
     "Chun-Yi Huang, Hsiao-Wei Liao, Teh-Min Hu", "RSC Advances 13(43): 29802–29808", "doi:10.1039/d3ra06596k"),
    ("2023", "How pre-coating of nanoparticles with serum proteins affects cellular uptake of positively charged nanoparticles?",
     "SC Chen, HC Chou, TM Hu, SJ Chiu", "日本毒性学会学術年会 第 50 回, P1-059S（研討會摘要）", ""),
    ("2022", "A general biphasic bodyweight model for scaling basal metabolic rate, glomerular filtration rate, and drug clearance from birth to adulthood",
     "Teh-Min Hu", "AAPS Journal 24(3): 67, 1–18", "Single author"),
    ("2022", "Co-delivery of nitric oxide and camptothecin using organic-inorganic composite colloidal particles for enhanced anticancer activity",
     "Li-Hao Chang, Teh-Min Hu", "Colloids and Surfaces A: Physicochemical and Engineering Aspects 632: 127740", ""),
    ("2021", "Organosilica colloids as nitric oxide carriers: pharmacokinetics and biocompatibility",
     "Hung-Chang Chou, Chih-Hui Lo, Li-Hao Chang, Shih-Jiuan Chiu, Teh-Min Hu", "Colloids and Surfaces B: Biointerfaces 208: 112136", "doi:10.1016/j.colsurfb.2021.112136"),
    ("2021", "Stable encapsulation of methylene blue in polysulfide organosilica colloids for fluorescent tracking of nanoparticle uptake in cells",
     "Guann-Tyng Chen, Teh-Min Hu", "ACS Omega 6(47): 32109–32119", ""),
    ("2021", "Solvent-mediated browning of proteins and amino acids",
     "Teh-Min Hu, Yi-Hua Chiang", "Biochemical and Biophysical Research Communications 36: 67–72", ""),
    ("2020", "Versatile composite hydrogels for drug delivery and beyond",
     "Yi-Hua Chiang, Meng-Ju Wu, Wei-Chin Hsu, Teh-Min Hu", "Journal of Materials Chemistry B 8: 8830–8837", ""),
    ("2019", "Turning proteins into hydrophobic floatable materials with multiple potential applications",
     "Teh-Min Hu, Hung-Chang Chou, Chien-Yu Lin", "Journal of Colloid and Interface Science 554: 166–176", ""),
    ("2019", "Facile green synthesis of organosilica nanoparticles by a generic “salt route”",
     "Teh-Min Hu, Chien-Yu Lin, Hung-Chang Chou, Meng-Ju Wu", "Journal of Colloid and Interface Science 539: 634–645", ""),
    ("2019", "Kinetics of fluoride-catalysed synthesis of organosilica colloids in aqueous solutions of amphiphiles",
     "Teh-Min Hu, Chien-Yu Lin, Meng-Ju Wu", "RSC Advances 9: 28028–28037", ""),
    ("2019", "Analysis of pharmacokinetic and pharmacodynamic parameters in EU- versus US-licensed reference biological products: are in vivo bridging studies justified for biosimilar development?",
     "Chien-Lung Tu, Yi-Lin Wang, Teh-Min Hu, Li-Feng Hsu", "BioDrugs, 1–10", ""),
    ("2018", "Formation of organosilica nanoparticles with dual functional groups and simultaneous payload entrapment",
     "Ya-Ling Su, Chien-Yu Lin, Shih-Jiuan Chiu, Teh-Min Hu", "Journal of Microencapsulation 35(4): 381–391", ""),
    ("2018", "S-Nitrosothiols (SNO) as light-responsive molecular activators for post-synthesis fluorescence augmentation in fluorophore-loaded nanospheres",
     "Shu-Yi Lin, Meng-Ren Wang, Shih-Jiuan Chiu, Chien-Yu Lin, Teh-Min Hu", "Journal of Materials Chemistry B 6(1): 153–164", ""),
    ("2017", "From a silane monomer to anisotropic buckled silica nanospheres: a polymer-mediated, solvent-free and one-pot synthesis",
     "Chih-Hui Lo, Teh-Min Hu", "Soft Matter 13(35): 5950–5960", ""),
    ("2017", "Famotidine-induced granulocytopenia: a case report",
     "Yu-Ju Chiao, Teh-Min Hu, Ya-Hui Ching, Cheng-Chih Hsieh", "Formosa Journal of Clinical Pharmacy 25(4): 319–325", ""),
    ("2016", "Preclinical evaluation of a nanoformulated antihelminthic, niclosamide, in ovarian cancer",
     "Chi-Kang Lin, Meng-Yi Bai, Teh-Min Hu, Yu-Chi Wang, Tai-Kuang Chao, Shao-Ju Weng, Rui Huang, Po-Hsuan Su, Hung-Cheng Lai", "Oncotarget 7(8): 8993–9006", "doi:10.18632/oncotarget.7113"),
    ("2015", "Silica Ouzo Effect: Amphiphilic Drugs Facilitate Nanoprecipitation of Polycondensed Mercaptosilanes",
     "Shih-Jiuan Chiu, Chien-Yu Lin, Hung-Chang Chou, Teh-Min Hu", "Langmuir 32(1): 211–220", "doi:10.1021/acs.langmuir.5b04048"),
    ("2015", "LbL Assembly of Albumin on Nitric Oxide-Releasing Silica Nanoparticles Using Suramin, a Polyanion Drug, as an Interlayer Linker",
     "Hung-Chang Chou, Shih-Jiuan Chiu, Teh-Min Hu", "Biomacromolecules 16(8): 2288–2295", "doi:10.1021/acs.biomac.5b00534"),
    ("2015", "An efficient S-NO-polysilsesquioxane nano-platform for the co-delivery of nitric oxide and an anticancer drug",
     "Meng-Ren Wang, Shih-Jiuan Chiu, Hung-Chang Chou, Teh-Min Hu", "Chemical Communications 51(86): 15649–15652", "doi:10.1039/c5cc06087g"),
    ("2014", "Nitric oxide-releasing S-nitrosothiol-modified silica/chitosan core–shell nanoparticles",
     "Wei-Lin Chang, Kang-Jen Peng, Teh-Min Hu, Shih-Jiuan Chiu, Ying-Ling Liu", "Polymer 57: 70–76", "doi:10.1016/j.polymer.2014.12.020"),
    ("2014", "Nitroxidative chemistry interferes with fluorescent probe chemistry: Implications for nitric oxide detection using 2,3-diaminonaphthalene",
     "Teh-Min Hu, Shih-Jiuan Chiu, Yu-Ming Hsu", "Biochemical and Biophysical Research Communications 451(2): 196–201", "doi:10.1016/j.bbrc.2014.07.097"),
    ("2014", "Versatile Synthesis of Thiol- and Amine-Bifunctionalized Silica Nanoparticles Based on the Ouzo Effect",
     "Shih-Jiuan Chiu, Su-Yuan Wang, Hung-Chang Chou, Ying-Ling Liu, Teh-Min Hu", "Langmuir 30(26): 7676–7686", "doi:10.1021/la501571u"),
    ("2014", "Direct Formation of S-Nitroso Silica Nanoparticles from a Single Silica Source",
     "Hung-Chang Chou, Shih-Jiuan Chiu, Ying-Ling Liu, Teh-Min Hu", "Langmuir 30(3): 812–822", "doi:10.1021/la4048215"),
    ("2012", "Superoxide Dismutase as a Novel Macromolecular Nitric Oxide Carrier: Preparation and Characterization",
     "Ssu-Han Chen, Shih-Jiuan Chiu, Teh-Min Hu", "International Journal of Molecular Sciences 13(11): 13985–14001", "doi:10.3390/ijms131113985"),
    ("2012", "Comparative kinetics of thiol oxidation in two distinct free-radical generating systems: SIN-1 versus AAPH",
     "Shan-Chu Ho, Shih-Jiuan Chiu, Teh-Min Hu", "Free Radical Research 46(10): 1190–1200", "doi:10.3109/10715762.2012.698010"),
    ("2011", "Kinetics of Redox Interaction between Cytochrome c and Thiols",
     "Teh-Min Hu, Shan Chu Ho", "31(3): 109–115", "doi:10.6136/jms.2011.31(3).109"),
    ("2010", "Similarity and dissimilarity of thiols as anti-nitrosative agents in the nitric oxide–superoxide system",
     "Teh-Min Hu, Shan-Chu Ho", "Biochemical and Biophysical Research Communications 404(3): 785–789", "doi:10.1016/j.bbrc.2010.12.059"),
    ("2010", "Allometric Scaling",
     "William L. Hayton, Teh-Min Hu", "Pharmaceutical Sciences Encyclopedia（參考書條目）, 1–28", "doi:10.1002/9780470571224.pse059"),
    ("2010", "Nitrosation-modulating effect of ascorbate in a model dynamic system of coexisting nitric oxide and superoxide",
     "Teh-Min Hu, Yu-Jen Chen", "Free Radical Research 44(5): 552–562", "doi:10.3109/10715761003667570"),
    ("2009", "Prediction of human drug clearance using a single-species, fixed-exponent allometric approach",
     "Teh-Min Hu, Shih Jiuan Chiu", "29(6): 331–339", ""),
    ("2009", "Architecture of the drug-drug interaction network",
     "Teh-Min Hu, William L. Hayton", "Journal of Clinical Pharmacy and Therapeutics 36(2): 135–143", "doi:10.1111/j.1365-2710.2009.01103.x"),
    ("2007", "Allometric Scaling",
     "William L. Hayton, Teh-Min Hu", "書籍章節, 頁 1009–1035", "doi:10.1002/9780470249031.ch29"),
    ("2006", "The kinetics of thiol-mediated decomposition of S-nitrosothiols",
     "Teh-Min Hu, Ta-Chuan Chou", "The AAPS Journal 8(3): E485–E492", "doi:10.1208/aapsj080357"),
    ("2006", "Kinetic Modeling of Nitric-Oxide-Associated Reaction Network",
     "Teh-Min Hu, William L. Hayton, Susan R. Mallery", "Pharmaceutical Research 23(8): 1702–1711", "doi:10.1007/s11095-006-9031-4"),
    ("2002", "Dynamic and biphasic modulation of nitrosation reaction by superoxide dismutases",
     "Teh-Min Hu, William L. Hayton, Mark A. Morse, Susan R. Mallery", "Biochemical and Biophysical Research Communications 295(5): 1125–1134", "doi:10.1016/s0006-291x(02)00820-3"),
    ("2001", "Allometric scaling of xenobiotic clearance: Uncertainty versus universality",
     "Teh-Min Hu, William L. Hayton", "AAPS PharmSci 3(4): 30–43", "doi:10.1208/ps030429"),
    ("1998", "Novel Single-Point Plasma or Saliva Dextromethorphan Method for Determining CYP2D6 Activity",
     "Oliver Yoa-Pu Hu, Hung-Shang Tang, Hsien-Yuan Lane, Wen-Ho Chang, Teh-Min Hu", "Journal of Pharmacology and Experimental Therapeutics 285(3): 955–960", "doi:10.1016/s0022-3565(24)37524-x"),
    ("1998", "The Clinical Significance of Assay Serum Collagen IV 7S Collagen in Patients with Hepatitis B-Related Liver Disease",
     "Hung-Shang Tang, Oliver Yoa-Pu Hu, You-Chen Chao, Ton-Ho Young, Teh-Min Hu", "18(5): 306–315", ""),
    ("1995", "Various measures of rate and extent of absorption in bioequivalent study of norfloxacin tablet",
     "Oliver Yoa-Pu Hu, Teh-Min Hu, Beiduo Chen, K. M. Chu", "中華藥學雜誌 (Zhōnghuá yàoxué zázhì) 47(4): 363–376", ""),
    ("1995", "The effect of aging on the pharmacokinetics of nalbuphine in rabbits",
     "Shung-Tai Ho, Jhi-Joung Wang, Oliver Yoa-Pu Hu, Teh-Min Hu", "Biopharmaceutics & Drug Disposition 16(8): 695–703", "doi:10.1002/bdd.2510160808"),
    ("1995", "Determination of Galactose in Human Blood by High‐Performance Liquid Chromatography: Comparison with an Enzymatic Method and Application to the Pharmacokinetic Study of Galactose in Patients with Liver Dysfunction",
     "Oliver Yoa-Pu Hu, Teh-Min Hu, Hung-Shang Tang", "Journal of Pharmaceutical Sciences 84(2): 231–235", "doi:10.1002/jps.2600840223"),
    ("1994", "Determination of guaiphenesin in anti-tussive pharmaceutical preparations containing dextromethorphan by first- and second-derivative ultraviolet spectrophotometry",
     "A.R. Lee, Teh-Min Hu", "Journal of Pharmaceutical and Biomedical Analysis 12(6): 747–752", "doi:10.1016/0731-7085(93)e0025-i"),
]


# DOIs found via OpenAlex/Crossref and matched by exact title (checked 2026-09).
DOIS = {
    "A general biphasic bodyweight model": "10.1208/s12248-022-00716-y",
    "Co-delivery of nitric oxide and camptothecin": "10.1016/j.colsurfa.2021.127740",
    "Stable encapsulation of methylene blue": "10.1021/acsomega.1c04877",
    "Solvent-mediated browning of proteins": "10.1016/j.bbrc.2020.12.047",
    "Versatile composite hydrogels": "10.1039/d0tb01360a",
    "Turning proteins into hydrophobic": "10.1016/j.jcis.2019.07.003",
    "Facile green synthesis of organosilica": "10.1016/j.jcis.2018.12.080",
    "Kinetics of fluoride-catalysed": "10.1039/c9ra05509f",
    "Analysis of pharmacokinetic and pharmacodynamic": "10.1007/s40259-019-00357-2",
    "Formation of organosilica nanoparticles with dual": "10.1080/02652048.2018.1508314",
    "S-Nitrosothiols (SNO)": "10.1039/c7tb02233f",
    "From a silane monomer": "10.1039/c7sm01043e",
    "Browned phenylalanine nanoparticles": "10.1016/j.colsurfa.2025.139015",
}


def doi(p):
    n = p[4]
    if n and n.startswith("doi:"):
        return n[4:]
    return next((v for k, v in DOIS.items() if p[1].startswith(k)), None)


def tlink(p):
    d = doi(p)
    return f'<a href="https://doi.org/{d}" target="_blank" rel="noopener">{p[1]}</a>' if d else p[1]


def cite(p):
    _, t, a, v, n = p
    d = doi(p)
    extra = (f' <span class="code">doi:{d}</span>' if d else "") + (" 單一作者。" if n == "Single author" else "")
    return f"{me(a)}. <em>{v}</em>.{extra}"



# Paper -> research areas, by title prefix (judged from titles; please review).
PAPER_AREAS = {
    "Nitric oxide-releasing nanoparticles for retinal": ["no", "organosilica"],
    "Solvent-mediated organocatalytic browning": ["browning"],
    "Structurally modified lysozyme": ["browning"],
    "Browned phenylalanine": ["browning"],
    "Albumin-based cryogels": ["hydrogel"],
    "A nano-platform harnessing": ["browning"],
    "Quantitative analysis of macrophage uptake": ["organosilica"],
    "Chemical reactivity of the tryptophan": ["browning"],
    "A general biphasic bodyweight model": ["pk"],
    "Co-delivery of nitric oxide and camptothecin": ["no"],
    "Organosilica colloids as nitric oxide carriers": ["no", "organosilica"],
    "Stable encapsulation of methylene blue": ["organosilica"],
    "Solvent-mediated browning of proteins": ["browning"],
    "Versatile composite hydrogels": ["hydrogel"],
    "Turning proteins into hydrophobic": ["hydrogel"],
    "Facile green synthesis of organosilica": ["organosilica"],
    "Kinetics of fluoride-catalysed": ["organosilica"],
    "Analysis of pharmacokinetic and pharmacodynamic": ["pk"],
    "Formation of organosilica nanoparticles with dual": ["organosilica"],
    "S-Nitrosothiols (SNO)": ["no"],
    "From a silane monomer": ["organosilica"],
    "Silica Ouzo Effect": ["organosilica"],
    "LbL Assembly of Albumin": ["no", "organosilica"],
    "An efficient S-NO-polysilsesquioxane": ["no", "organosilica"],
    "Nitric oxide-releasing S-nitrosothiol-modified silica": ["no", "organosilica"],
    "Versatile Synthesis of Thiol- and Amine": ["organosilica"],
    "Direct Formation of S-Nitroso Silica": ["no", "organosilica"],
    "Superoxide Dismutase as a Novel Macromolecular": ["no"],
    "Allometric Scaling": ["pk"],
    "Allometric scaling of xenobiotic": ["pk"],
    "Prediction of human drug clearance": ["pk"],
}


def areas_of(p):
    return next((v for k, v in PAPER_AREAS.items() if p[1].startswith(k)), [])


def area_count(aid):
    return sum(aid in areas_of(p) for p in PUBS)


def pubs_by_year():
    names = "{" + ",".join(f'"{i}":"{t}"' for i, t, _ in AREAS) + "}"
    out = (f"<div id=\"area-banner\" class=\"area-banner\" hidden data-names='{names}'>"
           '<span>目前顯示：<strong id="area-name"></strong>相關論文，共 <span id="area-n"></span> 篇（已反白）</span>'
           '<a href="publications.html" id="area-clear">顯示全部</a></div>')
    for y in dict.fromkeys(p[0] for p in PUBS):
        rows = entries([("", tlink(p), cite(p)) for p in PUBS if p[0] == y], lead=False)
        items = iter(p for p in PUBS if p[0] == y)
        rows = re.sub(r"<li>", lambda _: f'<li data-areas="{" ".join(areas_of(next(items)))}">', rows)
        out += f"<h2>{y}</h2>" + rows
    return out




# ---- News -------------------------------------------------------------------------
NEWS = [
    ("2026-09-12", "藥學系 10 週年慶頒獎，胡德民教授發表得獎感言",
     "國立陽明交通大學藥學系於 2026 年 9 月 12 日舉辦 10 週年慶，胡德民教授（第三任系主任）上台領獎並致詞。",
     [("assets/news/pharmacy-10th-award.jpg", "胡德民教授在藥學系 10 週年慶上領獎，背景投影片寫著「胡德民 教授（第三任系主任）」"),
      ("assets/news/pharmacy-10th-speech.jpg", "胡德民教授在藥學系 10 週年慶上發表得獎感言")],
     "https://pharmacy.nycu.edu.tw/10-%E9%80%B1%E5%B9%B4%E5%B0%88%E5%8D%80/", "藥學系 10 週年專區"),
]


def news_html(root, limit=None):
    out = ""
    for d, t, txt, imgs, link, ltxt in NEWS[:limit]:
        pics = "".join(f'<figure><img src="{root}{p}" alt="{a}" loading="lazy"></figure>' for p, a in imgs)
        out += (f'<article class="news"><span class="meta">{d}</span><div><h3>{t}</h3><p class="muted">{txt}</p>'
                f'{f"<p class=small><a href=\"{link}\">{ltxt} →</a></p>" if link else ""}'
                f'{f"<div class=news-photos>{pics}</div>" if pics else ""}</div></article>')
    return out


# ---- Alumni (graduate students supervised by Prof. Hu; thesis titles as given) --------
ALUMNI = [
    ("2026", "陳薇彭 Chen, Wei-Peng", "國立陽明交通大學 藥學系碩士班",
     "Chemical Characterization of Solvent-Mediated Browning of Amino Acids and the Derived Nanoparticles"),
    ("2025", "林婉芸 Lin, Wan-Yun", "國立陽明交通大學 藥學系碩士班",
     "Investigation of Nanoparticle Formation by Solvent-Mediated Browning Reaction of Phenylalanine"),
    ("2025", "金紹楷 Chin, Shao-Kai", "臺北醫學大學 藥學系碩士班",
     "A Nano-Drug Delivery System Based on Solvent-Mediated Browning Reaction of Tryptophan and Basic Amino Acids: Optimization, Potential Pharmaceutical Applications, and Material Characterization"),
    ("2024", "張芷榕 Chang, Chih-Jung", "國立陽明交通大學 藥學系碩士班",
     "Browned Lysozyme: Characterization and Potential Pharmaceutical Application"),
    ("2024", "林欣慧 Lin, Hsin-Hui", "臺北醫學大學 藥學系碩士班",
     "Nanoparticle drug delivery systems based on the novel browning reaction of biogenic amines（共同指導教授：林美香博士）"),
    ("2024", "徐瑋秦 Hsu, Wei-Chin", "國立陽明交通大學 藥學系學士班",
     "An Albumin-Based Floatable Gastro-Retentive Drug Delivery System"),
    ("2023", "梁嘉安 Liang, Jia-An", "國立陽明交通大學 藥學系碩士班",
     "Exploring the Browning Reaction of Combinatorial Amino Acids for Applications in Nano Drug Delivery"),
    ("2023", "黃駿逸 Huang, Chun-Yi", "國立陽明交通大學 藥學系碩士班",
     "A Chemical and Pharmaceutical Study of a Novel Amino Acid Reaction System with Potential Applications in Drug Delivery"),
    ("2023", "夏銘 Hsia, Ming", "國立陽明交通大學 藥物科學院藥學系學士班",
     "Anticancer Activity of Tryptophan-Derived Novel Maillard Reaction System"),
    ("2021", "周宏璋 Chou, Hung-Chang", "臺北醫學大學 藥學系博士班",
     "Pharmacokinetics of Organosilica Nano-Delivery Systems"),
    ("2020", "陳冠廷 Chen, Guan-Ting", "國立陽明大學 生物藥學研究所碩士班",
     "Polysulfide Organosilica Nano-Delivery Systems for Methylene Blue: Preparation, Characterization, Photodynamic Activity and Cell-Uptake Study"),
    ("2020", "張立皓 Chang, Li-Hao", "國立陽明大學 生物藥學研究所碩士班",
     "Simultaneous Delivery of Nitric Oxide and Camptothecin Using Hybrid Nanoparticles"),
    ("2018", "吳孟儒 Wu, Meng-Ju", "國立陽明大學 生物藥學研究所碩士班",
     "Co-Delivery of Nitric Oxide and Mitoxantrone Using Organosilica Nanoparticles: Preparation, Characterization, and Anticancer Activities"),
    ("2017", "羅智暉 Lo, Chih-Hui", "國防醫學院 藥學研究所碩士班",
     "Synthesis and Characterization of Nitric Oxide-Releasing Silica Nanoparticles by a Polymer-Assisted, One-Pot Method"),
    ("2016", "林書儀 Lin, Shu-Yi", "國防醫學院 藥學研究所碩士班",
     "Photophysicochemical and Photobiological Properties of Nanosilica-based Nitric oxide/Theranostics Co-Delivery Systems"),
    ("2015", "王孟仁 Wang, Meng-Jen", "國防醫學院 藥學研究所碩士班",
     "Nano-Silica Drug-Delivery Systems for Co-Delivering Nitric Oxide and Doxorubicin"),
    ("2013", "王思元 Wang, Su-Yuan", "臺北醫學大學 藥學系碩士班",
     "Preparation and Characterization of Thiol and Amine Bifunctionalized Silica Nanoparticles: Application to Delivery of Antisense Oligonucleotides"),
    ("2011", "張良敏 Chang, Liang-Min", "國防醫學院 藥學研究所碩士班",
     "Kinetic Study of Cancer-Cell-Mediated Extracellular Metabolism of S-Nitrosothiols"),
]

# ---- Home ------------------------------------------------------------------------
page("index.html", "首頁", "TMH Laboratory",
     "我們研究藥物遞送系統：膠體奈米粒子、水凝膠與釋放一氧化氮的載體，並結合藥動學模型。"
     "實驗室位於台北陽明校區，隸屬國立陽明交通大學藥學系。",
     f'''<h2>實驗室簡介</h2>
<div class="intro">
<div>
<h3>胡德民 教授 <span class="zh">{PI}</span></h3>
<p class="muted small">國立陽明交通大學 藥學系 教授</p>
<p>胡德民教授於國防醫學院取得藥學學士與碩士學位，2002 年取得美國俄亥俄州立大學藥劑學博士。1989 年至 2016 年任教於國防醫學院，2016 年轉任國立陽明大學，2022 年 8 月至 2025 年兼任藥學系系主任，並於 2025 年 7 月至 2026 年 7 月赴奧克蘭大學藥學院擔任訪問教授。</p>
<p><a href="people/principal-investigator.html">完整簡歷：學歷、經歷與學術服務 →</a></p>
</div>
<dl class="facts">
<dt>學歷</dt>
<dd>美國俄亥俄州立大學 藥劑學博士（2002）<br>國防醫學院 藥學碩士、學士</dd>
<dt>現職</dt>
<dd>國立陽明交通大學 藥學系 教授</dd>
<dt>專長</dt>
<dd>藥劑學 · 生物藥劑學 · 藥動學 · 物理藥學</dd>
<dt>聯絡</dt>
<dd><a href="mailto:tehmin@nycu.edu.tw">tehmin@nycu.edu.tw</a></dd>
</dl>
</div>
<h2>研究領域</h2>
{grid([("有機矽奈米粒子", "以綠色、單鍋法合成有機矽與矽膠膠體粒子，可在合成時包覆藥物，並以螢光追蹤細胞攝取。"),
       ("一氧化氮遞送", "開發攜帶並釋放一氧化氮的複合粒子，可單獨使用或與抗癌藥物共同遞送；已獲美國與台灣專利。"),
       ("水凝膠與蛋白質材料", "用於藥物遞送的複合水凝膠，以及將蛋白質轉變為疏水、可漂浮材料的方法。")])}
<p><a href="research/areas.html">所有研究領域 →</a></p>
<h2>近期發表</h2>
{entries([(p[0], tlink(p), cite(p)) for p in PUBS[:2]])}
<p><a href="publications.html">所有論文 →</a></p>
<h2>最新消息</h2>
{news_html("", 2)}
<p><a href="news.html">所有消息 →</a></p>
<h2>加入我們</h2>
<p>歡迎有意願的碩士、博士生與博士後研究員來信洽詢，請附上研究興趣與履歷給主持人。</p>
<p><a class="btn" href="people/principal-investigator.html#contact">聯絡主持人</a></p>''')

# ---- Research --------------------------------------------------------------------
AREAS = [
    ("organosilica", "有機矽奈米粒子", "以綠色、單鍋法合成有機矽與矽膠膠體粒子（通用的「鹽途徑」、氟離子催化動力學），包括異向性皺褶矽球，以及具雙重官能基、可於形成時同步包覆藥物的粒子。"),
    ("no", "一氧化氮遞送", "攜帶並釋放一氧化氮的複合粒子、與喜樹鹼共遞送以增強抗癌活性、光響應的 S-亞硝基硫醇活化劑，以及以釋放一氧化氮的奈米粒子保護視網膜免受藍光傷害；並研究有機矽載體的藥動學、巨噬細胞攝取與生物相容性。"),
    ("hydrogel", "水凝膠與蛋白質材料", "用於藥物遞送的多功能複合水凝膠、將蛋白質轉變為疏水可漂浮材料的方法，以及以白蛋白冷凍凝膠作為胃滯留漂浮載體。"),
    ("browning", "褐變化學與功能性奈米材料", "利用溶劑、胺基酸與蛋白質的褐變反應，製備兩性離子奈米粒子與具抗氧化功能的修飾蛋白質（如溶菌酶），並探討其膠體穩定性。"),
    ("pk", "藥動學縮放", "以體重雙相模型，將基礎代謝率、腎絲球過濾率與藥物清除率由出生縮放至成年；並探討生物藥品的藥動／藥效可比性。"),
]

page("research/areas.html", "研究", "研究領域",
     "藥物遞送載體，以及引導其應用的藥動學原理。",
     '<div class="grid3">' + "".join(
         f'<div><h3>{t}</h3><p class="muted">{d}</p>'
         f'<p class="small"><a href="../publications.html#area={i}">相關論文（{area_count(i)} 篇）→</a></p></div>'
         for i, t, d in AREAS) + '</div>' +
     '<p class="muted small">內容依據實驗室 2017–2026 年發表論文整理，請主持人確認並潤飾用語。</p>')
page("research/technologies.html", "研究", "技術與專利",
     "實驗室開發的平台與智慧財產。",
     entries([("美國專利", "Complex particles for delivering nitric oxide, method of producing the same, and application of the same", "Hu et al. US 10,098,966 B2，2018-10-16 核准。"),
              ("中華民國專利", "遞送一氧化氮之複合粒子、其製備方法及其應用", "發明專利 I637013，專利期限 2018-10-01 至 2037-06-29。"),
              ("技術平台", "有機矽奈米粒子合成", "於水相中以單鍋法製備功能性有機矽膠體粒子。")]))

# ---- Publications ----------------------------------------------------------------
page("publications.html", "發表論文", "發表論文",
     "已發表論文，依年份排列，老師的姓名以粗體標示。",
     pubs_by_year())

# ---- People ----------------------------------------------------------------------
NAME_ROW = f'''<div class="profile-top">
<div>
<p class="eyebrow">人員 · 主持人</p>
<h1>胡德民 <span class="zh">{PI}</span></h1>
<p class="role">教授</p>
<p class="muted">國立陽明交通大學 藥學系</p>
<p class="small"><a href="mailto:tehmin@nycu.edu.tw">tehmin@nycu.edu.tw</a> · <span style="white-space:nowrap">(02) 2826-7000 分機 67984</span></p>
</div>
<img class="photo-img" src="../assets/people/hu-teh-min.jpg" alt="胡德民教授" width="560" height="700">
</div>
<nav class="jump" aria-label="本頁目錄"><a href="#biography">簡介</a><a href="#education">學歷</a><a href="#appointments">經歷</a><a href="#service">學術服務</a><a href="#expertise">專長</a><a href="#patents">專利</a><a href="#contact">聯絡方式</a></nav>'''
page("people/principal-investigator.html", "人員", "主持人", None,
     f'''<h2 id="biography">簡介</h2>
<p>胡德民教授專長為藥劑學，研究聚焦於藥物遞送系統與藥動學。他於 1989 年、1993 年分別取得國防醫學院藥學系學士與藥學研究所碩士學位，並於 2002 年取得美國俄亥俄州立大學藥劑學博士學位。</p>
<p>1989 年至 2016 年間任教於國防醫學院藥學系，歷任助教、助理教授與副教授；2016 年轉任國立陽明大學藥學系副教授，2020 年起為國立陽明交通大學藥學系教授；2022 年 8 月至 2025 年兼任系主任，並於 2025 年 7 月至 2026 年 7 月赴紐西蘭奧克蘭大學藥學院擔任訪問教授。</p>
<p>在實驗室之外，胡教授亦服務於台灣藥學界，包括衛生福利部中華藥典與藥品相關諮議委員會，以及台灣藥學會。</p>
<h2 id="education">學歷</h2>
{entries(EDU, wide=True)}
<h2 id="appointments">經歷</h2>
{entries(POS, wide=True)}
<h2 id="service">學術服務</h2>
{entries(SERVICE, wide=True)}
<h2 id="expertise">專長</h2>
<p>藥劑學 · 生物藥劑學 · 藥動學 · 物理藥學</p>
<h2 id="patents">專利</h2>
{entries([("美國", "Complex particles for delivering nitric oxide, method of producing the same, and application of the same", "Hu et al. US 10,098,966 B2，2018-10-16。"),
          ("台灣", "遞送一氧化氮之複合粒子、其製備方法及其應用", "發明專利 I637013，專利期限 2018-10-01 至 2037-06-29。")], wide=True)}
<h2 id="contact">聯絡方式</h2>
<p>國立陽明交通大學 藥學系<br>
電子郵件：<a href="mailto:tehmin@nycu.edu.tw">tehmin@nycu.edu.tw</a><br>
辦公室電話：(02) 2826-7000 分機 67984<br>
實驗室電話：(02) 2826-7000 分機 66460</p>
<p><a href="https://scholar.nycu.edu.tw/zh/persons/teh-min-hu/" target="_blank" rel="noopener">陽明交大學術資料庫個人頁面 →</a></p>''',
     top=NAME_ROW)
page("people/members.html", "人員", "成員", "實驗室的成員，包含歷屆畢業的學長姊。",
     '<h2>現有成員</h2>' +
     entries([("碩士生", "謝宜敏 Hsieh, Yi-Min", ""), ("大專生", "陳俞璇 Tan, Yu-Xuan", "")], wide=True) +
     '<h2>歷屆畢業生</h2>' +
     '<p class="muted small">論文皆由胡德民教授指導（林欣慧為共同指導）。</p>' +
     entries([(y, n, f"{s}<br><em>{t}</em>") for y, n, s, t in ALUMNI], wide=True) +
     '<h2>Welcome to TMH lab family!!!!</h2>' +
     '<div class="gallery">' +
     photo([("assets/people/life/promotion-2019-turkey.jpg", "慶祝聚餐的烤火雞"),
            ("assets/people/life/promotion-2019-toast.jpg", "師生舉杯合影"),
            ("assets/people/life/promotion-2019-group.jpg", "餐廳內團體合影")],
           "2019-11-27", "恭賀老師榮升教授。", root="../") +
     photo([("assets/people/life/lab-dinner-2021.jpg", "實驗室聚餐合影")],
           "2021-11-19", "實驗室聚餐。", root="../") +
     photo([("assets/people/life/auckland-pharmacy-group.jpg", "於奧克蘭大學藥學系合影"),
            ("assets/people/life/auckland-fmhs-photo.jpg", "於奧克蘭大學醫學與健康科學院前合影")],
           "2026-04 – 2026-06", "赴紐西蘭奧克蘭大學藥學系 Darren Svirskis 教授實驗室進行三個月研究交流。", root="../") +
     photo([("assets/people/life/hamilton-lake-parkrun-2026.jpg", "於紐西蘭 Hamilton Lake parkrun 合影")],
           "2026-07-04", "於紐西蘭 Hamilton Lake parkrun。", root="../") +
     '</div>' +
     empty("更多團體照與生活照將於取得後補上。"))

page("news.html", "最新消息", "最新消息", "論文發表、獲獎、演講與實驗室動態。", news_html("../"[:0]))

# ---- Resources -------------------------------------------------------------------
LINKS = [("校內系統", "陽明交大單一入口", "https://portal.nycu.edu.tw/#/login?redirect=%2F", "登入校內各項行政與學習系統。"),
         ("系所", "陽明交大藥學系", "https://pharmacy.nycu.edu.tw/", "國立陽明交通大學藥學系官方網站。"),
         ("學術檔案", "陽明交大學術資料庫：胡德民", "https://scholar.nycu.edu.tw/zh/persons/teh-min-hu/", "老師的官方學術個人頁，含研究專長、論文清單與引用統計。"),
         ("校內系統", "課程查詢", "https://timetable.nycu.edu.tw/", "查詢各學期開設的課程與時間。"),
         ("校內系統", "儀器預約", "https://ircbooking.nycu.edu.tw/irc/", "預約校內共用儀器。"),
         ("校內系統", "環安系統", "https://oehs.nycu.edu.tw/portal/manulogin", "環境安全衛生相關系統，需登入。"),
         ("校內系統", "圖書館", "https://www.lib.nycu.edu.tw/", "查詢館藏、電子資源與期刊資料庫。")]
page("resources/useful-links.html", "相關連結", "相關連結", "實驗室與校內常用的外部網站。",
     entries([(c, f'<a href="{u}" target="_blank" rel="noopener">{t}</a>', d) for c, t, u, d in LINKS]))

# ---- Members pages (content is encrypted at build time) ------------------------
def mpage(slug, title, lede, body, nav_cur=None):
    page(f"members/{slug}.html", "成員專區", title, lede, body, member=True, nav_cur=nav_cur)



INSTRUMENTS = [("balance", "分析天平（Analytical Balance）", "METTLER TOLEDO ME204",
                "四位數精密秤量，是配製溶液、秤量藥品最基本也最關鍵的一步。", "assets/instruments/balance.jpg"),
               ("ph-meter", "pH meter", "METTLER TOLEDO SevenCompact S220",
                "量測水溶液的酸鹼值（pH）與離子濃度，使用前須以標準緩衝液校正。", "assets/instruments/ph-meter.jpg"),
               ("uv-vis", "紫外-可見光分光光度計（UV-Vis）", "Shimadzu UV-1900i Plus",
                "量測樣品在紫外光與可見光波段的吸收光譜，用於濃度測定與反應動力學。", "assets/instruments/uv-vis.jpg"),
               ("dls", "動態光散射儀（DLS）與 Zeta 電位分析儀", "Malvern Zetasizer Nano",
                "量測奈米粒子的粒徑分布、多分散性指數（PDI）與 Zeta 電位。", "assets/instruments/dls-zetasizer.jpg"),
               ("lyophilizer", "減壓濃縮機（Freeze dryer）", "VirTis BTP-9EGE0X",
                "以冷凍乾燥（凍乾）方式移除樣品中的水分，分外槽與內槽兩種使用方式。", "assets/instruments/lyophilizer.jpg"),
               ("centrifuge", "冷凍離心機（Refrigerated Centrifuge）", "Thermo Scientific Heraeus Megafuge 8R",
                "以離心力分離樣品中不同密度或大小的成分，可控制轉速與溫度。", "assets/instruments/centrifuge.jpg")]

mpage("instruments", "儀器設備", "共用儀器的原理、操作方式與注意事項。",
      '<ul class="list inst">' + "".join(
          f'<li><a class="inst-img" href="instruments/{k}.html"><img src="../{img}" alt="{t}"></a>'
          f'<div><p class="label">{m}</p><h3><a href="instruments/{k}.html">{t}</a></h3><p class="muted">{d}</p>'
          f'<p><a href="instruments/{k}.html">原理與操作影片 →</a></p></div></li>' for k, t, m, d, img in INSTRUMENTS) + '</ul>' +
      f'<p class="muted small">更多儀器將陸續加入。{PH}</p>')

mpage("instruments/balance", "分析天平（Analytical Balance）", "以 METTLER TOLEDO ME204 進行精密秤量。",
      f'''<p class="small"><a href="../instruments.html">← 儀器設備</a></p>
<figure class="hero"><img src="../../assets/instruments/balance.jpg" alt="METTLER TOLEDO ME204 分析天平"></figure>
<p class="muted small">圖片為儀器產品照片，實際型號請以實驗室的儀器為準。</p>
<p><strong>位置：</strong>715-2（本實驗室內）</p>
<h2>為什麼秤重這麼重要</h2>
<p>幾乎每個實驗都是從秤重開始：配製溶液的濃度、藥品劑量、反應物的當量比，都是以秤得的重量為基礎去計算出來的。秤重如果不準，後面所有依這個重量計算出的結果都會跟著偏差，而且這個誤差通常不會在後續步驟中被發現，只會被一路帶到最終數據裡。這也是為什麼秤重是整個實驗最基本、卻也最容易被輕忽的一步。</p>
<h3>秤重的準確度要求</h3>
<p>Ph. Eur. 與 USP 的通則都提到：實際秤得的量只要在指定量的 10% 以內，並以實際秤得的重量計算結果，就符合「about」的用法；但方法若要求「accurately weighed（精確秤重）」，秤重就必須符合天平本身的準確度規格，不能只用「差不多」帶過。</p>
<p>天平的誤差是固定的絕對值，量越小、相對誤差就越大：以 ±0.1 mg 的誤差為例，秤 100 mg 只有 0.1% 誤差，秤 5 mg 就變成 2%，秤到 1 mg 已達到「about」10% 的門檻——但這只是最寬鬆的標準。業界對「精確秤重」的判斷嚴格得多：以本機（ME204，重複性約 0.08–0.1 mg）搭配秤重界慣用的 0.10% 準確度與 2 倍安全係數換算，最小可秤重量其實落在約 <strong>160–400 mg</strong>。若要秤的量落在這個門檻以下，該換用讀數更細的五位數天平（如 0.01 mg 的半微量天平），或提高秤取量（例如稀釋後秤取較大體積）。</p>
<p class="muted small">參考資料：<a href="https://faq.edqm.eu/pages/viewpage.action?pageId=1376853" target="_blank" rel="noopener">EDQM《What accuracy is required for measuring quantities stated in Ph. Eur. texts?》</a>、<a href="https://www.usp.org/frequently-asked-questions/balances-and-weighing-analytical-balance" target="_blank" rel="noopener">USP《FAQs: Balances and Weighing on an Analytical Balance》</a>、<a href="https://www.troemner.com/reference-center/weights-reference-center/USP-41-Weighing-Requirements-for-Balances" target="_blank" rel="noopener">Troemner《USP 41 Weighing Requirements for Balances》</a>。天平重複性規格引用自型錄公開數值，實際數字請以本實驗室儀器的校正紀錄為準。</p>
<h2>操作方式</h2>
<div class="videos">{video("mmgiehwrK54", "How to Use an Analytical Balance", "BioNetwork")}</div>
<h3>使用規定</h3>
<ul class="bullets">
<li>使用結束後用刷子將秤盤清乾淨，再關機。</li>
</ul>
<h2>管理者</h2>
<p>本實驗室</p>''', nav_cur="members/instruments.html")

mpage("instruments/ph-meter", "pH meter", "以 METTLER TOLEDO SevenCompact S220 量測 pH 值與離子濃度。",
      f'''<p class="small"><a href="../instruments.html">← 儀器設備</a></p>
<figure class="hero"><img src="../../assets/instruments/ph-meter.jpg" alt="METTLER TOLEDO SevenCompact S220 pH meter"></figure>
<p class="muted small">圖片為儀器產品照片，實際型號請以實驗室的儀器為準。</p>
<p><strong>位置：</strong>715-2（本實驗室內）</p>
<h2>原理</h2>
<p>pH 電極內的玻璃薄膜對氫離子敏感，會依溶液中氫離子濃度產生電位差，儀器將這個電位差換算成 pH 值。因為電極的電位反應會隨時間與使用而改變，測量前必須以已知 pH 值的標準緩衝液校正，確認電極仍然準確。</p>
<div class="videos">{video("zJTQLce-WC8", "pH Meter | working of glass electrode of pH meter", "Quick Biochemistry Basics")}</div>
<h2>操作方式</h2>
<h3>TMH Lab｜pH Meter 校正流程</h3>
<ol class="bullets">
<li>開機（ON）。</li>
<li>清洗 pH 電極，並以無塵紙／擦拭紙輕輕吸乾電極表面。</li>
<li>將電極置於第一個校正緩衝液（pH 7.00），按 Cal；完成後以去離子水沖洗並擦乾電極。</li>
<li>將電極置於第二個校正緩衝液（pH 4.00），按 Cal；完成後以去離子水沖洗並擦乾電極。</li>
<li>將電極置於第三個校正緩衝液（pH 10.00），按 Cal；完成後以去離子水沖洗並擦乾電極。</li>
<li>按 End 完成三點校正，並確認 Slope ≥ 95%。</li>
<li>按 Save 儲存校正結果。</li>
<li>測量樣品時按 Read 讀值。</li>
</ol>
<h3>使用規定</h3>
<ul class="bullets">
<li>使用時務必填寫實驗本：姓名／實驗室（TMH）／使用時間；使用後檢查沒問題，填上 OK。</li>
<li>如需提前預約時段，請在紀錄本上寫下姓名與時間，並用螢光筆畫記，標示該時段已被預約。</li>
</ul>
<h2>管理者</h2>
<p>本實驗室</p>''', nav_cur="members/instruments.html")

mpage("instruments/dls", "動態光散射儀（DLS）與 Zeta 電位分析儀", "以 Malvern Zetasizer Nano 量測粒徑、PDI 與 Zeta 電位。",
      f'''<p class="small"><a href="../instruments.html">← 儀器設備</a></p>
<figure class="hero"><img src="../../assets/instruments/dls-zetasizer.jpg" alt="Malvern Zetasizer Nano 動態光散射與 Zeta 電位分析儀"></figure>
<p class="muted small">圖片為儀器產品照片，實際型號請以實驗室的儀器為準。</p>
<p><strong>位置：</strong>守仁樓 717 室</p>
<h2>原理</h2>
<h3>粒徑：動態光散射（DLS）</h3>
<p>懸浮在液體中的粒子會不斷做布朗運動：粒子越小動得越快，粒子越大動得越慢。雷射照射樣品時，散射光的強度會隨粒子運動而快速起伏。儀器量測這些起伏的相關函數，得到粒子的擴散係數，再依 Stokes–Einstein 方程式換算成<strong>流體動力學直徑</strong>（hydrodynamic diameter），並同時給出粒徑分布的寬窄，即多分散性指數（PDI）。</p>
<h3>Zeta 電位：電泳光散射</h3>
<p>粒子表面帶電時，在電場下會向相反電性的電極移動。儀器量測移動速度（電泳移動率），再以 Henry 方程式換算成 <strong>Zeta 電位</strong>。Zeta 電位的絕對值越大，粒子之間的靜電排斥越強，通常膠體越穩定，常以 ±30 mV 作為粗略的經驗參考。</p>
<div class="videos">{video("ET6S03GeMKE", "Introduction to Dynamic Light Scattering Analysis", "Malvern Panalytical")}{video("GlCvY-nLVa0", "Zeta Potential Tutorial | Part 1: Intro to Zeta Potential", "nanoComposix")}</div>
<h2>操作方式</h2>
<p>請先看下面兩支影片了解一般的量測流程，再依本實驗室的儀器設定與規定操作。</p>
<div class="videos">{video("XORue2LN9RU", "Dynamic Light Scattering (DLS)", "Yoon Idea Lab")}{video("WN8cr6b2Gbo", "Zeta Potential Tutorial | Part 2: Performing a Measurement", "nanoComposix")}</div>
<h3>上機前應注意事項</h3>
<ul class="bullets">
<li>樣品要適當稀釋，避免氣泡與灰塵，必要時先過濾。</li>
<li>確認分散介質（黏度、折射率）與量測溫度的設定正確。</li>
<li>樣品槽在使用前後都要清潔乾淨，避免交叉污染。</li>
<li>量測 Zeta 電位要使用專用的樣品槽，並注意電極附近不要有氣泡。</li>
</ul>
<h3>使用規定</h3>
<ul class="bullets">
<li>使用時務必填寫實驗本：姓名／實驗室（TMH）／使用時間；使用後檢查沒問題，填上 OK。</li>
<li>如需提前預約時段，請在紀錄本上寫下姓名與時間，並用螢光筆畫記，標示該時段已被預約。</li>
</ul>
{empty("開機順序、樣品準備、量測參數與量測後清潔的步驟，將於整理後補上。")}
<h2>管理者</h2>
<p>林宥欣老師實驗室</p>''', nav_cur="members/instruments.html")

mpage("instruments/uv-vis", "紫外-可見光分光光度計（UV-Vis）", "以 Shimadzu UV-1900i Plus 量測吸收光譜。",
      f'''<p class="small"><a href="../instruments.html">← 儀器設備</a></p>
<figure class="hero"><img src="../../assets/instruments/uv-vis.jpg" alt="Shimadzu UV-1900i Plus 紫外-可見光分光光度計"></figure>
<p class="muted small">圖片為儀器產品照片，實際型號請以實驗室的儀器為準。</p>
<p><strong>位置：</strong>守仁樓 717 室</p>
<h2>原理</h2>
<p>樣品中的分子吸收特定波長的光，會使電子從基態躍遷到激發態。UV-Vis 分光光度計掃描一段波長範圍，量測光通過樣品前後的強度差異，畫出<strong>吸收光譜</strong>。依 Beer–Lambert 定律，吸光度（A）與樣品濃度（c）、光徑長（l）成正比：A = εcl（ε 為莫耳吸光係數），因此可用於定量分析與反應動力學的追蹤（例如奈米粒子生成、褐變反應的顏色變化）。</p>
<div class="videos">{video("gGRMtq7hvHc", "Spectroscopy || Beer-Lambert's Law", "Rethink Biology")}</div>
<h2>操作方式</h2>
<h3>使用規定</h3>
<ul class="bullets">
<li>使用時務必填寫實驗本：姓名／實驗室（TMH）／使用時間；使用後檢查沒問題，填上 OK。</li>
<li>如需提前預約時段，請在紀錄本上寫下姓名與時間，並用螢光筆畫記，標示該時段已被預約。</li>
</ul>
<h3>參考文件</h3>
<p><a href="../../assets/instruments/manuals/uv-vis-manual.pdf" target="_blank" rel="noopener">LabSolutions 操作說明（PDF，掃描版）→</a></p>
{empty("操作影片與本實驗室的量測流程，將於整理後補上。")}
<h2>管理者</h2>
<p>陳日榮老師實驗室</p>''', nav_cur="members/instruments.html")


mpage("instruments/lyophilizer", "減壓濃縮機（Freeze dryer）", "以冷凍乾燥移除樣品中的水分。位於生物醫學大樓 710 室。",
      f'''<p class="small"><a href="../instruments.html">← 儀器設備</a></p>
<figure class="hero"><img src="../../assets/instruments/lyophilizer.jpg" alt="VirTis BTP-9EGE0X 減壓濃縮機（冷凍乾燥機）"></figure>
<p class="muted small">圖片為儀器產品照片，實際型號請以實驗室的儀器為準。</p>
<p><strong>型號：</strong>VirTis BTP-9EGE0X<br><strong>位置：</strong>生物醫學大樓 710 室</p>
<h2>原理</h2>
<p>樣品先冷凍成固態，再置於真空環境中：在低壓下，冰不經過液態直接昇華成水蒸氣，逐漸將水分移除，過程中樣品維持在低溫，可避免高溫造成的結構破壞或變性，適合用於保存蛋白質、奈米粒子等對熱敏感的樣品。</p>
<div class="videos">{video("3DsaVLiwshY", "The Process of Freeze Drying (Lyophilization)", "BioNetwork")}</div>
<h2>操作方式</h2>
<div class="warn"><p><strong>本機嚴禁使用【Isotope】及有機溶劑。</strong></p></div>
<h3>外槽</h3>
<ul class="bullets">
<li>外槽可直接使用，不需事先預約。</li>
<li>使用前請先至生物醫學大樓 7F 共儀中心預借凍乾瓶：本實驗室的凍乾瓶與外槽接口不合，須另外借用相容的瓶子。</li>
</ul>
<h3>內槽</h3>
<ul class="bullets">
<li>使用前須先至預約系統線上預約。</li>
<li>使用容量以槽內體積的 1/2 為原則；容量低於槽內體積 1/4 者，請改放外管。</li>
<li>內槽的使用須配合外槽的開關機時間。</li>
</ul>
<h3>參考文件</h3>
<p><a href="../../assets/instruments/manuals/lyophilizer-manual.pdf" target="_blank" rel="noopener">廠商操作手冊（PDF）→</a></p>
<h2>管理者</h2>
<p>生物醫學大樓 7F 共儀中心<br>
分機：65660<br>
<a href="https://www.nycu.edu.tw/ord/ch/app/machine/view?module=machine&id=1780&serno=9f489cae-1f61-48a6-8197-91217f9dfcb0" target="_blank" rel="noopener">校內設備網頁 →</a></p>''', nav_cur="members/instruments.html")

mpage("instruments/centrifuge", "冷凍離心機（Refrigerated Centrifuge）", "以 Thermo Scientific Heraeus Megafuge 8R 進行樣品離心。",
      f'''<p class="small"><a href="../instruments.html">← 儀器設備</a></p>
<figure class="hero"><img src="../../assets/instruments/centrifuge.jpg" alt="Thermo Scientific Heraeus Megafuge 8R 冷凍離心機"></figure>
<p class="muted small">圖片為儀器產品照片，實際型號請以實驗室的儀器為準。</p>
<p><strong>位置：</strong>守仁樓 715-8</p>
<p><a href="https://www.thermofisher.com/order/catalog/product/75007213" target="_blank" rel="noopener">廠商產品頁 →</a></p>
<h2>原理</h2>
<p>轉子高速旋轉時，樣品中密度較大的成分受到的離心力較大，會較快沉降到離心管底部，密度較小的成分則留在上層，藉此依大小或密度分離樣品中的不同成分。本機可同時控制轉速與溫度，適合處理需要低溫的樣品。</p>
<h2>操作方式</h2>
<h3>使用規定</h3>
<ul class="bullets">
<li>使用時務必填寫實驗本：姓名／實驗室（TMH）／使用時間；使用後檢查沒問題，填上 OK。</li>
<li>使用前務必平衡：離心管需對稱放置，兩側重量相同，避免離心時震動或損壞儀器。</li>
</ul>
{empty("開機順序、轉速與溫度設定、使用後清潔的步驟，將於整理後補上。")}
<h2>管理者</h2>
<p>廖曉偉老師實驗室</p>''', nav_cur="members/instruments.html")

SOFTWARE = [
    ("文獻管理", "Zotero", "https://www.zotero.org/download/", "閱讀論文的好夥伴：整理文獻、做筆記，還能在 Word 裡直接插入引用文獻與產生參考文獻列表。"),
    ("統計與繪圖", "R 與 RStudio", "https://rstudio-education.github.io/hopr/starting.html", "統計分析與精美的數據圖。連結是 R 與 RStudio 的安裝教學。"),
    ("程式語言", "Python", "https://www.python.org/downloads/", "資料分析與自動化。連結為官方下載頁。"),
    ("統計與繪圖", "Prism", None, "製作數據圖表與統計分析的好夥伴。安裝檔放在實驗室雲端硬碟，需以被授權的帳號登入。 <a href=\"https://drive.google.com/drive/folders/1D24fpavqvcxRGg3rMNiuacbnilZupFrf?usp=drive_link\" target=\"_blank\" rel=\"noopener\">前往雲端硬碟下載 →</a>"),
    ("層析軟體", "HPLC 軟體（UC 5.1.16）", None, "HPLC 儀器的資料處理軟體。安裝檔放在實驗室雲端硬碟，需以被授權的帳號登入。 <a href=\"https://drive.google.com/drive/folders/1D24fpavqvcxRGg3rMNiuacbnilZupFrf?usp=drive_link\" target=\"_blank\" rel=\"noopener\">前往雲端硬碟下載 →</a>"),
]
mpage("software-tools", "軟體與工具", "實驗室常用的分析與繪圖軟體。",
      entries([(c, f'<a href="{u}" target="_blank" rel="noopener">{t}</a>' if u else t, d) for c, t, u, d in SOFTWARE], wide=True))
mpage("shared-documents", "公用文件", "實驗室成員共用的文件、範本與表單。",
      '<p>文件放在實驗室的雲端硬碟，請以被授權的帳號登入後開啟。</p><p><a class="btn" href="https://drive.google.com/drive/folders/13rax2xm57rDNdb7uApnQfdFKuc0ICXjw?usp=drive_link" target="_blank" rel="noopener">開啟公用文件資料夾</a></p>')

print("built")
