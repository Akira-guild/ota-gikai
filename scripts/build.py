"""data/sessions と data/summaries から静的サイトを site/ に作る。"""
import html, json, re, os, pathlib, shutil, datetime, urllib.parse

SITE_NAME = "やさしい大田区議会"
SITE_EN = "OTA CITY ASSEMBLY, IN PLAIN WORDS"
OPERATOR = "小宮あきら"  # 運営者として表示する名前
# 公開先のURL（末尾は /）。環境変数 SITE_URL でも上書きできる（GitHub Actions で自動設定）
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/") + "/" if os.environ.get("SITE_URL") else ""

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "site"
E = lambda s: html.escape(str(s or ""), quote=True)

KIND_LABEL = {"kucho": "区長提出議案", "giin": "議員提出議案", "iinkai": "委員会提出議案",
              "doi": "同意（人事）", "seichin": "請願・陳情", "hokoku": "報告"}
KIND_ORDER = ["kucho", "giin", "iinkai", "doi", "seichin", "hokoku"]
DETAIL_KINDS = {"kucho", "giin", "iinkai", "doi", "seichin"}

CATEGORIES = [
    ("子育て・教育", "kosodate", ["保育", "子ども", "こども", "児童", "学校", "学童", "教育", "幼稚園", "乳児", "入学", "給食", "小学校", "中学校", "図書館"]),
    ("福祉・医療", "fukushi", ["福祉", "介護", "高齢", "障害", "障がい", "医療", "健康", "国民健康保険", "後期高齢", "生活保護", "補聴器", "シルバーパス", "特別養護"]),
    ("防災・安全", "bousai", ["防災", "災害", "消防", "避難", "耐震", "防犯", "安全", "危機"]),
    ("まちづくり・道路", "machi", ["道路", "都市計画", "区画整理", "駅", "公園", "橋", "まちづくり", "住宅", "建築", "自転車", "駐車", "民泊", "空家", "空き家", "新空港線"]),
    ("環境・ごみ", "kankyo", ["環境", "ごみ", "廃棄物", "清掃", "リサイクル", "脱炭素", "緑", "喫煙", "騒音"]),
    ("産業・観光", "sangyo", ["産業", "工業", "商店", "観光", "中小企業", "羽田", "ものづくり", "国際", "空港"]),
    ("施設・工事", "shisetsu", ["工事", "請負契約", "改修", "改築", "改築", "施設", "取得", "指定管理"]),
    ("予算・決算", "yosan", ["予算", "決算", "基金", "税", "手数料", "使用料"]),
    ("人事", "jinji", ["委員", "任命", "選任", "推薦", "同意", "職員", "給与", "報酬", "期末手当"]),
    ("議会・行政のしくみ", "gyosei", ["議会", "選挙", "条例の整備", "行政手続", "個人情報", "情報公開", "意見書", "決議"]),
]
CAT_SLUG = {c[0]: c[1] for c in CATEGORIES}

AREAS = ["蒲田", "大森", "羽田", "池上", "馬込", "田園調布", "糀谷", "六郷", "矢口", "雪谷", "千束", "久が原",
         "鵜の木", "下丸子", "嶺町", "平和島", "昭和島", "京浜島", "城南島", "東海", "入新井", "新井宿", "山王",
         "大岡山", "石川台", "洗足池", "萩中", "多摩川", "田園調布", "南馬込", "中央", "西蒲田", "東蒲田"]
AREAS = list(dict.fromkeys(AREAS))

GLOSSARY = [
    ("原案可決", "出された案を、そのまま認めること。"),
    ("否決", "出された案を、認めないこと。"),
    ("認定", "決算（前の年度のお金の使い方）を、議会が認めること。"),
    ("全会一致", "議決に加わった議員が全員賛成したこと。"),
    ("賛成者多数", "反対した会派・議員もいたが、賛成のほうが多かったこと。"),
    ("区長提出議案", "区長（区役所）が議会に出した案。予算・条例・工事の契約など。"),
    ("議員提出議案", "議員が出した案。一定の人数の議員の賛成が必要。"),
    ("委員会提出議案", "議会の委員会がまとめて出した案。意見書など。"),
    ("請願・陳情", "区民などが議会にお願いを出すしくみ。請願は議員の紹介が必要、陳情は不要。"),
    ("採択・不採択", "請願・陳情のお願いを、議会として受け入れる（採択）か、受け入れない（不採択）か。"),
    ("継続", "その会期では結論を出さず、次の会期以降も話し合うこと。"),
    ("補正予算", "年度の途中で、最初に決めた予算を足したり減らしたりすること。"),
    ("決算", "1年間にお金を実際にいくら集め、いくら使ったかのまとめ。"),
    ("条例", "大田区だけで通用するきまり。議会の議決で作る・変える。"),
    ("専決処分", "急ぎの場合などに、議会を開かずに区長が決めること。あとで議会に報告する。"),
    ("請負契約", "工事などを会社に頼む契約。大きな金額のものは議会の議決が必要。"),
    ("付託", "本会議から委員会に、くわしく話し合うよう任せること。"),
    ("会派", "考えの近い議員のグループ。"),
    ("定例会", "年4回、決まった時期に開く議会。臨時会は必要なときに開く。"),
    ("意見書", "議会として、国や都などに意見を伝える文書。"),
]


def norm(s):
    return re.sub(r"[\s　（）()「」]", "", (s or "")).translate(str.maketrans("０１２３４５６７８９", "0123456789"))


def split_result(r):
    r = (r or "").replace("\n", "")
    m = re.match(r"(.*?)（(.*?)）$", r)
    return (m.group(1), m.group(2)) if m else (r, "")


def result_tone(res):
    if res in ("原案可決", "可決", "認定", "同意", "採択", "承認"): return "ok"
    if res in ("否決", "原案否決", "不採択", "不同意", "不認定"): return "ng"
    if res in ("継続", "取下げ"): return "mid"
    return "none"


def easy_title(t, kind):
    """説明がまだない議案に、機械的に少しだけ読みやすい見出しをつける（意味は変えない）。"""
    t = (t or "").replace("\n", " ")
    t2 = t.replace("大田区立", "区立").replace("大田区", "")
    if kind == "seichin":
        return t2
    m = re.match(r"(.*)の一部を改正する条例$", t2)
    if m: return f"「{m.group(1)}」を変える"
    m = re.match(r"(.*)を廃止する条例$", t2)
    if m: return f"「{m.group(1)}」をなくす"
    m = re.match(r"(.*?)(?:その他)?工事.*請負契約について$", t2)
    if m: return f"{m.group(1)}の工事を会社に頼む契約"
    m = re.match(r"(.*)請負契約について$", t2)
    if m: return f"{m.group(1)}の契約"
    m = re.match(r"(令和.+年度)(.*)歳入歳出決算$", t2)
    if m: return f"{m.group(1)}の{m.group(2) or '一般会計'}で、お金をどう使ったか（決算）"
    m = re.match(r"(令和.+年度)(.*)補正予算（(.*)）$", t2)
    if m: return f"{m.group(1)}の{m.group(2)}の予算を組み直す（{m.group(3)}補正）"
    m = re.match(r"(令和.+年度)(.*)予算$", t2)
    if m: return f"{m.group(1)}の{m.group(2)}の予算"
    m = re.match(r"(.*)の指定管理者の指定について$", t2)
    if m: return f"{m.group(1)}を運営する団体を決める"
    m = re.match(r"(.*)条例$", t2)
    if m and kind in ("kucho", "giin"): return f"新しいきまり「{m.group(1)}条例」"
    return t2


def guess_category(t):
    for name, _, kws in CATEGORIES:
        if any(k in t for k in kws): return name
    return "議会・行政のしくみ"


def guess_areas(text):
    return [a for a in AREAS if a in text]


def slug_no(no):
    return re.sub(r"[^0-9A-Za-z]+", "-", norm(no).replace("第", "-").replace("号", "")).strip("-") or "x"


# ---------- データ読み込み ----------
def load():
    sessions = []
    for f in sorted((ROOT / "data" / "sessions").glob("*.json")):
        sessions.append(json.loads(f.read_text(encoding="utf-8")))
    sessions.sort(key=lambda s: (s["era"], s["id"]), reverse=True)
    summaries = {}
    for f in sorted((ROOT / "data" / "summaries").glob("*.json")):
        sid = re.match(r"(r\d\d-\d[tr])", f.stem).group(1)
        summaries.setdefault(sid, {}).update(json.loads(f.read_text(encoding="utf-8")))
    items = []
    apath = ROOT / "data" / "archived_pdfs.json"
    archived = json.loads(apath.read_text(encoding="utf-8")) if apath.exists() else {}
    for s in sessions:
        taido = {}
        factions = []
        for p in s["pages"]:
            if p["kind"] == "taido":
                factions = [x.replace("｜", "ー") for x in p.get("factions", [])]
                for r in p["rows"]:
                    taido[norm(r["title"])] = {k.replace("｜", "ー"): v for k, v in r["votes"].items()}
        s["factions"] = factions
        s["items"] = []
        pending = all(not r.get("result") for p in s["pages"] if p["kind"] == "kucho" for r in p["rows"]) and \
            any(p["kind"] == "kucho" for p in s["pages"])
        s["pending"] = pending
        for p in s["pages"]:
            k = p["kind"]
            if k not in KIND_LABEL: continue
            for i, r in enumerate(p["rows"]):
                title = (r.get("title") or "").replace("\n", " ")
                if not title: continue
                no = r.get("no") or str(i + 1)
                res, how = split_result(r.get("result"))
                if res == "-": res = ""
                sm = summaries.get(s["id"], {}).get(f"{k}-{norm(no)}")
                it = {
                    "sid": s["id"], "session": s["name"], "kind": k, "no": no, "title": title,
                    "date": (r.get("date") or "").strip("（）()"), "result": res, "how": how,
                    "committee": r.get("committee", "") if r.get("committee") not in ("なし", "-") else "",
                    "votes": taido.get(norm(title)), "page_url": p["url"],
                    "pdfs": p["pdfs"] + [x for x in archived.get(s["id"], []) if x["kind"] == k],
                    "summary": sm, "pending": not res and k != "hokoku",
                }
                it["id"] = f"{s['id']}-{k}-{slug_no(no)}"
                it["headline"] = sm["headline"] if sm else easy_title(title, k)
                it["category"] = (sm or {}).get("category") or guess_category(title)
                it["areas"] = list(dict.fromkeys(((sm or {}).get("areas") or []) + guess_areas(title)))
                it["amount"] = (sm or {}).get("amount", "")
                s["items"].append(it)
                items.append(it)
    return sessions, items


# ---------- 共通部品 ----------
CSS = """
:root{--brand:#b8325a;--brand-d:#9a2448;--accent:#2e7d4f;--ink:#1f1b1d;--sub:#6a6064;--line:#ece4e6;--bg:#faf6f4;--card:#fff;
--ok:#2e7d4f;--okbg:#e7f3ec;--ng:#3a3a3a;--ngbg:#ececec;--mid:#3d3a10;--midbg:#d3d1af;--uguisu:#928c36;--chip:#fbeef1;
--grad:linear-gradient(100deg,#9a2448 0%,#c23a62 55%,#d65a7c 100%)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--brand:#f08aa6;--brand-d:#f5a9bd;--accent:#6fcf97;--ink:#efe8ea;--sub:#aaa0a4;--line:#3a2e33;--bg:#171214;--card:#221a1d;
--ok:#6fcf97;--okbg:#14301f;--ng:#d6d6d6;--ngbg:#333;--mid:#efeab0;--midbg:#4a4720;--uguisu:#b3ac4a;--chip:#3a2029}}
:root[data-theme="dark"]{--brand:#f08aa6;--brand-d:#f5a9bd;--accent:#6fcf97;--ink:#efe8ea;--sub:#aaa0a4;--line:#3a2e33;--bg:#171214;--card:#221a1d;
--ok:#6fcf97;--okbg:#14301f;--ng:#d6d6d6;--ngbg:#333;--mid:#efeab0;--midbg:#4a4720;--uguisu:#b3ac4a;--chip:#3a2029}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Noto Sans JP",system-ui,sans-serif;line-height:1.85;font-size:16px;letter-spacing:.03em;-webkit-font-smoothing:antialiased}
a{color:var(--brand-d)}
.wrap{max-width:760px;margin:0 auto;padding:0 16px 64px}
header.site{background:var(--card);position:sticky;top:0;z-index:5;border-bottom:1px solid var(--line)}
header.site .wrap{padding-top:12px;padding-bottom:12px;display:flex;align-items:center;gap:10px}
.logo{font-weight:700;font-size:17px;text-decoration:none;color:var(--ink);display:flex;align-items:center;gap:9px;letter-spacing:.06em}
.logo svg{width:30px;height:30px;flex:none}
.logo span{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .logo span{background:linear-gradient(100deg,#f08aa6,#f7b9c9);-webkit-background-clip:text;background-clip:text}}
:root[data-theme="dark"] .logo span{background:linear-gradient(100deg,#f08aa6,#f7b9c9);-webkit-background-clip:text;background-clip:text}
header nav{margin-left:auto;display:flex;gap:14px;font-size:14px}
header nav a{color:var(--sub);text-decoration:none}
h1{font-size:25px;line-height:1.5;margin:28px 0 12px;letter-spacing:.05em}
h2{font-size:19px;margin:0 0 14px;line-height:1.45;letter-spacing:.05em;position:relative;padding-top:14px}
h2::before{content:"";position:absolute;top:0;left:1px;width:32px;height:5px;border-radius:3px;background:var(--grad)}
h2 small{font-size:12px;color:var(--sub);font-weight:500;margin-left:8px;letter-spacing:.1em}
section{margin:40px 0}
.card{background:var(--card);border-radius:14px;padding:18px 18px;border:1px solid var(--line)}
.hero{margin-top:22px;border-radius:20px;padding:30px 22px;color:#fff;background:var(--grad);position:relative;overflow:hidden}
.hero h1{margin:0 0 8px;font-size:28px;color:#fff}
.hero p{margin:0;opacity:.95}
.hero .en{font-size:11px;letter-spacing:.2em;opacity:.85}
.hero svg.plane{position:absolute;right:-18px;bottom:-26px;width:170px;opacity:.22}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;text-align:center}
.stat b{display:block;font-size:24px;color:var(--brand)}
.stat span{font-size:12px;color:var(--sub)}
.compare{display:grid;gap:10px}
.compare .before{font-size:14px;color:var(--sub);background:var(--bg);border-radius:10px;padding:10px 12px}
.compare .after{font-weight:700;font-size:17px;background:var(--chip);border-radius:10px;padding:10px 12px}
.compare .arrow{text-align:center;color:var(--accent);font-weight:700}
.list{display:grid;gap:10px}
.item{display:block;text-decoration:none;color:inherit;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;transition:border-color .15s}
.item:hover{border-color:var(--brand)}
.item .meta{font-size:12px;color:var(--sub);display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center}
.item .hl{font-weight:700;font-size:16.5px;line-height:1.6;margin:4px 0 2px}
.item .amt{font-size:13px;color:var(--accent);font-weight:700}
.item .off{font-size:12.5px;color:var(--sub)}
.badge{display:inline-block;font-size:12px;font-weight:700;border-radius:999px;padding:1px 10px;line-height:1.7}
.badge.ok{color:var(--ok);background:var(--okbg)}.badge.ng{color:var(--ng);background:var(--ngbg)}
.badge.mid{color:var(--mid);background:var(--midbg);box-shadow:inset 0 0 0 1.5px var(--uguisu)}.badge.none{color:var(--sub);background:var(--bg)}
.badge.soon{color:#fff;background:var(--accent)}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{display:inline-block;text-decoration:none;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:999px;padding:5px 14px;font-size:14px}
.chip:hover{border-color:var(--brand);color:var(--brand-d)}
.chip small{color:var(--sub);margin-left:4px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.tile{display:block;text-decoration:none;color:inherit;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}
.tile b{display:block}.tile span{font-size:13px;color:var(--sub)}
.votes{width:100%;border-collapse:collapse;font-size:14px}
.votes td{padding:7px 4px;border-bottom:1px solid var(--line)}
.votes td:last-child{text-align:right}
.v-yes{color:var(--ok);font-weight:700}.v-no{color:var(--ng);font-weight:700}.v-oth{color:var(--sub)}
.points{margin:0;padding-left:1.2em}.points li{margin:4px 0}
dl.kv{display:grid;grid-template-columns:7em 1fr;gap:4px 10px;font-size:14px;margin:0}
dl.kv dt{color:var(--sub)}dl.kv dd{margin:0}
.note{font-size:13px;color:var(--sub)}
.notice{font-size:13.5px;background:var(--midbg);color:var(--mid);border-radius:10px;padding:10px 12px;border-left:6px solid var(--uguisu)}
.btn{display:inline-block;background:var(--brand);color:#fff;text-decoration:none;border:0;border-radius:999px;padding:9px 20px;font:inherit;font-weight:700;cursor:pointer}
.btn:hover{background:var(--brand-d)}
.crumbs{font-size:13px;color:var(--sub);margin-top:16px}
.crumbs a{color:var(--sub)}
footer .operator{font-size:15px;color:var(--ink);margin-bottom:4px}
footer .operator b{font-weight:900;font-size:18px;letter-spacing:.08em}
footer{border-top:1px solid var(--line);margin-top:40px;padding-top:20px;font-size:13px;color:var(--sub)}
.kindh{font-size:15px;margin:22px 0 10px;color:var(--sub)}
details summary{cursor:pointer;color:var(--brand-d)}
@media (max-width:520px){.hero h1{font-size:23px}.grid2{grid-template-columns:1fr}.stat b{font-size:20px}header nav{gap:10px;font-size:13px}}
"""

LOGO = """<svg viewBox="0 0 32 32" aria-hidden="true"><defs><linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="#9a2448"/><stop offset="1" stop-color="#d65a7c"/></linearGradient></defs><rect x="1" y="1" width="30" height="30" rx="9" fill="url(#g)"/><circle cx="16.00" cy="10.30" r="5" fill="#fff"/><circle cx="21.90" cy="14.58" r="5" fill="#fff"/><circle cx="19.64" cy="21.52" r="5" fill="#fff"/><circle cx="12.36" cy="21.52" r="5" fill="#fff"/><circle cx="10.10" cy="14.58" r="5" fill="#fff"/><circle cx="16" cy="16.5" r="3" fill="#f3c74f"/></svg>"""
PLANE = """<svg class="plane" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32.00" cy="19.00" r="11" fill="#fff"/><circle cx="44.36" cy="27.98" r="11" fill="#fff"/><circle cx="39.64" cy="42.52" r="11" fill="#fff"/><circle cx="24.36" cy="42.52" r="11" fill="#fff"/><circle cx="19.64" cy="27.98" r="11" fill="#fff"/><circle cx="32" cy="32" r="6" fill="#9a2448" opacity=".35"/></svg>"""  # 区の花・ウメ


def page(title, body, depth=0, desc=""):
    up = "../" * depth
    full = f"{title}｜{SITE_NAME}" if title != SITE_NAME else f"{SITE_NAME}｜大田区議会で決まったことを、ふだんの言葉で"
    desc = desc or "大田区議会の議案・予算・条例・請願・陳情で何が決まったかを、ふだんの言葉で説明する非公式サイト。会派ごとの賛否と区の資料へのリンクつき。"
    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(full)}</title><meta name="description" content="{E(desc)}">
<meta property="og:title" content="{E(full)}"><meta property="og:description" content="{E(desc)}"><meta property="og:type" content="website">
<meta property="og:site_name" content="{E(SITE_NAME)}"><meta name="twitter:card" content="summary_large_image">
{f'<meta property="og:image" content="{SITE_URL}og.png"><meta name="twitter:image" content="{SITE_URL}og.png">' if SITE_URL else ""}
<link rel="icon" href="{up}favicon.png" type="image/png"><link rel="apple-touch-icon" href="{up}apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{up}style.css"></head><body>
<header class="site"><div class="wrap"><a class="logo" href="{up}index.html">{LOGO}<span>{E(SITE_NAME)}</span></a>
<nav><a href="{up}kore.html">これから</a><a href="{up}index.html#find">探す</a><a href="{up}yougo.html">用語</a></nav></div></header>
<main class="wrap">{body}
<footer>
<p class="operator">運営：<b>{E(OPERATOR)}</b></p>
<p>このサイトは<strong>大田区・大田区議会の公式サイトではありません</strong>。大田区議会ホームページで公開されている議決結果・議案書をもとに、プログラムとAIで自動的に作っています。人による内容の確認はしていません。大事な判断の前には、各ページの「元の資料」で必ず確かめてください。</p>
<p>会派ごとの賛否は、大田区議会ホームページ「意見が異なった議案に対する各会派の態度」の記載のとおりに、すべての会派を同じ形で載せています。</p>
<p><a href="{up}about.html">このサイトについて</a> ・ <a href="{up}yougo.html">用語集</a> ・ <a href="https://www.city.ota.tokyo.jp/gikai/" rel="noopener">大田区議会（公式）</a></p>
<p>最終更新：{datetime.datetime.now().strftime('%Y年%-m月%-d日 %H:%M')}</p>
</footer></main></body></html>"""


def item_card(it, up=""):
    tone = result_tone(it["result"])
    badge = f'<span class="badge soon">これから</span>' if it["pending"] else \
        (f'<span class="badge {tone}">{E(it["result"])}</span>' if it["result"] else "")
    how = f'<span>{E(it["how"])}</span>' if it["how"] else ""
    no = f'第{E(it["no"])}号' if it["kind"] in ("kucho", "giin", "iinkai") else E(it["no"]) if it["kind"] == "seichin" else ""
    amt = f'<div class="amt">{E(it["amount"])}</div>' if it["amount"] else ""
    off = f'<div class="off">{E(it["title"])}</div>' if it["headline"] != it["title"] else ""
    href = f'{up}b/{it["id"]}.html' if it["kind"] in DETAIL_KINDS else E(it["page_url"])
    return f"""<a class="item" href="{href}"><div class="meta">{badge}{how}<span>{E(it["session"])}</span><span>{KIND_LABEL[it["kind"]]} {no}</span></div>
<div class="hl">{"【否決された案】" if tone == "ng" else ""}{E(it["headline"])}</div>{amt}{off}</a>"""


def vote_table(it, factions):
    v = it["votes"]
    if v:
        rows = "".join(
            f'<tr><td>{E(f)}</td><td class="{"v-yes" if x == "賛成" else "v-no" if x == "反対" else "v-oth"}">{E(x or "—")}</td></tr>'
            for f, x in v.items())
        yes = sum(1 for x in v.values() if x == "賛成"); no = sum(1 for x in v.values() if x == "反対")
        return f'<p class="note">賛成 {yes}会派・反対 {no}会派</p><table class="votes">{rows}</table>'
    if it["how"] == "全会一致":
        return "<p>議決に加わった<strong>すべての会派が賛成</strong>しました（全会一致）。</p>"
    if it["pending"]:
        return "<p class=\"note\">まだ議決されていません。議決のあと、各会派の態度が公開されます。</p>"
    if it["kind"] == "seichin":
        return "<p class=\"note\">請願・陳情の会派ごとの態度は、大田区議会の公開資料にこの形では載っていません。</p>"
    return "<p class=\"note\">会派ごとの態度の記載はありません。</p>"


def item_page(it, factions):
    sm = it["summary"]
    if sm and sm.get("basis") == "title": sm = None
    tone = result_tone(it["result"])
    if it["pending"]:
        status = '<span class="badge soon">これから決まる</span>'
    else:
        status = f'<span class="badge {tone}">{E(it["result"] or "—")}</span> <span class="note">{E(it["how"])}</span>'
    no = f'第{E(it["no"])}号' if it["kind"] in ("kucho", "giin", "iinkai") else E(it["no"]) if it["kind"] == "seichin" else ""
    if sm:
        pts = "".join(f"<li>{E(p)}</li>" for p in sm.get("points", []))
        expl = f'<section class="card"><h2>どういうこと？</h2><ul class="points">{pts}</ul>' + \
               (f'<p><strong>金額：</strong>{E(sm["amount"])}</p>' if sm.get("amount") else "") + \
               '<p class="note">この説明は議案書をもとにAIが書いたものです。正確な内容は元の資料で確かめてください。</p></section>'
    else:
        if it["summary"]:
            expl = '<section class="card"><h2>どういうこと？</h2><p class="note">この会期の議案書は、大田区のサイトから外されていて手に入りませんでした。そのため、上の見出しは<strong>件名をふだんの言葉に言い換えただけ</strong>で、中身の説明はありません。</p></section>'
        else:
            expl = '<section class="card"><h2>どういうこと？</h2><p class="note">この議案のくわしい説明はまだありません。下の「元の資料」で議案書を読めます。</p></section>'
    pdf = "".join(f'<li><a href="{E(p["url"])}" rel="noopener">{E(p["label"])}</a></li>' for p in it["pdfs"])
    areas = "".join(f'<a class="chip" href="../area/{E(a)}.html">{E(a)}</a>' for a in it["areas"])
    body = f"""<div class="crumbs"><a href="../index.html">ホーム</a> › <a href="../s/{it["sid"]}.html">{E(it["session"])}</a></div>
<p style="margin:16px 0 0">{status}</p>
<h1>{E(it["headline"])}</h1>
{'<p class="notice">この案は<strong>認められませんでした（' + E(it["result"]) + '）</strong>。上の見出しは「出された案の中身」です。</p>' if tone == "ng" else ""}
<p class="note">正式な名前：{E(it["title"])}</p>
{expl}
<section class="card"><h2>だれが賛成した？</h2>{vote_table(it, factions)}</section>
<section class="card"><h2>基本の情報</h2><dl class="kv">
<dt>会期</dt><dd><a href="../s/{it["sid"]}.html">{E(it["session"])}</a></dd>
<dt>種類</dt><dd>{KIND_LABEL[it["kind"]]} {no}</dd>
<dt>議決日</dt><dd>{E(it["date"]) or "—"}</dd>
<dt>委員会</dt><dd>{E(it["committee"]) or "—"}</dd>
<dt>分野</dt><dd><a href="../c/{CAT_SLUG.get(it["category"], "gyosei")}.html">{E(it["category"])}</a></dd>
</dl>{f'<div class="chips" style="margin-top:12px">{areas}</div>' if areas else ""}</section>
<section class="card"><h2>元の資料</h2><ul><li><a href="{E(it["page_url"])}" rel="noopener">大田区議会：{KIND_LABEL[it["kind"]]}（{E(it["session"])}）</a></li>{pdf}</ul></section>"""
    return page(it["headline"], body, 1, desc=f'{it["session"]} {it["title"]}')


WRITTEN = []


def write(path, text):
    if path.endswith(".html") and path != "404.html": WRITTEN.append(path)
    p = OUT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def build():
    sessions, items = load()
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    write("style.css", CSS)
    for f in (ROOT / "assets").glob("*"):
        shutil.copy(f, OUT / f.name)
    (OUT / ".nojekyll").write_text("")
    decided = [i for i in items if i["kind"] in DETAIL_KINDS and not i["pending"]]
    explained = [i for i in items if i["summary"] and i["summary"].get("basis") != "title"]
    fac_by_sid = {s["id"]: s["factions"] for s in sessions}

    for it in items:
        if it["kind"] in DETAIL_KINDS:
            write(f'b/{it["id"]}.html', item_page(it, fac_by_sid[it["sid"]]))

    # 会期ページ
    for s in sessions:
        parts = []
        for k in KIND_ORDER:
            its = [i for i in s["items"] if i["kind"] == k]
            if not its: continue
            cards = "".join(item_card(i, "../") for i in its)
            if k == "hokoku":
                parts.append(f'<details><summary class="kindh">{KIND_LABEL[k]}（{len(its)}件）— 区から議会への報告。議決はしません</summary><div class="list">{cards}</div></details>')
            else:
                parts.append(f'<h3 class="kindh">{KIND_LABEL[k]}（{len(its)}件）</h3><div class="list">{cards}</div>')
        n_ex = sum(1 for i in s["items"] if i["summary"] and i["summary"].get("basis") != "title")
        pend = '<p class="notice">この会期は開会中です。議案はまだ議決されていません。</p>' if s["pending"] else ""
        body = f"""<div class="crumbs"><a href="../index.html">ホーム</a> › 会期</div><h1>{E(s["name"])}</h1>
{pend}<p class="note">全{len(s["items"])}件・くわしい説明あり{n_ex}件 ・ <a href="{E(s["url"])}" rel="noopener">大田区議会の該当ページ</a></p>{"".join(parts)}"""
        write(f's/{s["id"]}.html', page(s["name"], body, 1))

    # 分野
    for name, slug, _ in CATEGORIES:
        its = [i for i in items if i["category"] == name and i["kind"] in DETAIL_KINDS]
        its.sort(key=lambda i: (bool(i["summary"]), i["sid"]), reverse=True)
        body = f'<div class="crumbs"><a href="../index.html">ホーム</a> › 分野</div><h1>{E(name)}</h1><p class="note">{len(its)}件（説明のあるものが先）</p><div class="list">' + \
               "".join(item_card(i, "../") for i in its) + "</div>"
        write(f"c/{slug}.html", page(name, body, 1))

    # 地域
    area_count = {}
    for a in list(dict.fromkeys(AREAS + [x for i in items for x in i["areas"]])):
        its = [i for i in items if a in i["areas"] and i["kind"] in DETAIL_KINDS]
        if not its: continue
        area_count[a] = len(its)
        its.sort(key=lambda i: i["sid"], reverse=True)
        body = f'<div class="crumbs"><a href="../index.html">ホーム</a> › <a href="index.html">地域</a></div><h1>{E(a)}に関係すること</h1><p class="note">議案・請願・陳情の名前や説明に「{E(a)}」が出てくるもの {len(its)}件</p><div class="list">' + \
               "".join(item_card(i, "../") for i in its) + "</div>"
        write(f"area/{a}.html", page(f"{a}に関係すること", body, 1))
    area_chips = "".join(f'<a class="chip" href="{{up}}area/{E(a)}.html">{E(a)}<small>{n}</small></a>' for a, n in sorted(area_count.items(), key=lambda x: -x[1]))
    write("area/index.html", page("地域から探す", '<div class="crumbs"><a href="../index.html">ホーム</a> › 地域</div><h1>地域から探す</h1><div class="chips">' + area_chips.replace("{up}", "../") + "</div>", 1))

    # これから決まること
    pend_s = [s for s in sessions if s["pending"]]
    if pend_s:
        s = pend_s[0]
        its = [i for i in s["items"] if i["kind"] in DETAIL_KINDS]
        kore = f'<h1>これから決まること</h1><p>開会中の<strong>{E(s["name"])}</strong>に出されている議案です。まだ議決されていません。</p>' + \
               f'<p class="note"><a href="https://www.city.ota.tokyo.jp/gikai/kugikai_oshirase/kaiginittei.html" rel="noopener">会議日程（大田区議会）</a> ・ <a href="https://www.city.ota.tokyo.jp/gikai/hirakareta_gikai/boucho.html" rel="noopener">傍聴のご案内</a> ・ <a href="https://www.city.ota.tokyo.jp/gikai/hirakareta_gikai/g_chuukei/index.html" rel="noopener">議会中継</a></p>' + \
               '<div class="list">' + "".join(item_card(i) for i in its) + "</div>"
    else:
        kore = "<h1>これから決まること</h1><p>いま開会中の会期はありません。</p>"
    write("kore.html", page("これから決まること", kore))

    # 用語集
    g = "".join(f'<div class="card" style="margin-bottom:10px"><b>{E(w)}</b><div>{E(d)}</div></div>' for w, d in GLOSSARY)
    write("yougo.html", page("議会の言葉の説明（用語集）", f"<h1>議会の言葉の説明</h1>{g}"))

    # このサイトについて
    about = f"""<h1>このサイトについて</h1>
<div class="card"><p>大田区議会では、区の予算・条例・工事の契約・区民からの請願や陳情などが話し合われ、決められています。けれど、区の資料は正式な名前や専門の言葉で書かれていて、何が決まったのかがすぐにはわかりません。</p>
<p>このサイトは、大田区議会ホームページで公開されている情報をもとに、<strong>何が決まったのか・だれが賛成したのか</strong>を、ふだんの言葉でまとめ直したものです。</p></div>
<section><h2>データの出どころ</h2><ul>
<li>大田区議会「本会議」各会期のページ（区長提出議案・議員提出議案・委員会提出議案・同意・請願・陳情・報告）</li>
<li>同「意見が異なった議案に対する各会派の態度」</li>
<li>各議案の議案書（PDF）</li></ul>
<p class="note">取得は1秒以上の間隔をあけて行っています。</p></section>
<section><h2>説明文の書き方</h2><p>議案書の内容だけをもとに書き、資料にないことは足さない決まりにしています。説明は AI が書いており、人の確認はしていません。間違いがあるかもしれません。</p></section>
<section><h2>運営</h2><p><b style="font-weight:900">{E(OPERATOR)}</b> が個人で運営しています。</p></section>
<section><h2>中立について</h2><p>どの会派・議員の立場にも寄らず、会派ごとの賛否は区議会の公開資料の記載のまま、すべての会派を同じ形で載せています。</p></section>
<p class="notice">このサイトは大田区・大田区議会の公式サイトではありません。</p>"""
    write("about.html", page("このサイトについて", about))

    # トップ
    latest_decided = next(s for s in sessions if not s["pending"])
    latest = [i for i in latest_decided["items"] if i["kind"] in DETAIL_KINDS and i["summary"]][:6] or \
             [i for i in latest_decided["items"] if i["kind"] in DETAIL_KINDS][:6]
    ex = next((i for i in explained if not i["pending"] and i["amount"]), None)
    compare = ""
    if ex:
        compare = f"""<section><h2>このサイトがやっていること<small>WHAT WE DO</small></h2><div class="card compare">
<p style="margin:0">区の資料は、正式な名前や専門の言葉で書かれています。それを、何が決まったのかが一目でわかる言葉に直しています。</p>
<div class="before"><span class="note">区の資料では</span><br>第{E(ex["no"])}号議案 {E(ex["title"])}</div><div class="arrow">▼</div>
<div class="after"><span class="note" style="font-weight:400">このサイトでは</span><br>{E(ex["headline"])}</div>
<div class="grid2" style="margin-top:6px"><div class="tile"><b>何が決まった</b><span>ふだんの言葉で</span></div><div class="tile"><b>だれが賛成した</b><span>全会派を同じ形で</span></div></div></div></section>"""
    pick_pool = [{"u": f'b/{i["id"]}.html', "h": i["headline"], "s": i["session"]} for i in explained if not i["pending"]] or \
                [{"u": f'b/{i["id"]}.html', "h": i["headline"], "s": i["session"]} for i in decided]
    cat_tiles = "".join(
        f'<a class="tile" href="c/{slug}.html"><b>{E(name)}</b><span>{sum(1 for i in items if i["category"] == name and i["kind"] in DETAIL_KINDS)}件</span></a>'
        for name, slug, _ in CATEGORIES)
    top_areas = "".join(f'<a class="chip" href="area/{E(a)}.html">{E(a)}<small>{n}</small></a>'
                        for a, n in sorted(area_count.items(), key=lambda x: -x[1])[:16])
    sess_list = "".join(
        f'<a class="item" href="s/{s["id"]}.html"><div class="hl" style="margin:0">{E(s["name"])} {"<span class=\"badge soon\">開会中</span>" if s["pending"] else ""}</div>'
        f'<div class="note">全{len(s["items"])}件・説明あり{sum(1 for i in s["items"] if i["summary"] and i["summary"].get("basis") != "title")}件</div></a>' for s in sessions)
    kore_box = ""
    if pend_s:
        kore_box = f'<a class="item" href="kore.html" style="border-color:var(--accent)"><div class="meta"><span class="badge soon">開会中</span></div><div class="hl">{E(pend_s[0]["name"])}で、これから決まること {sum(1 for i in pend_s[0]["items"] if i["kind"] in DETAIL_KINDS)}件</div><div class="note">まだ議決されていない議案と日程 →</div></a>'
    body = f"""<div class="hero"><div class="en">{E(SITE_EN)}</div><h1>{E(SITE_NAME)}</h1>
<p>議会って、むずかしい言葉ばかり。<br>だから、ふだんの言葉に直しました。</p>{PLANE}</div>
<div class="stats"><div class="stat"><b>{len(sessions)}</b><span>会期</span></div><div class="stat"><b>{len(decided)}</b><span>議決など</span></div><div class="stat"><b>{len(explained)}</b><span>くわしい説明</span></div></div>
{f'<section>{kore_box}</section>' if kore_box else ''}
{compare}
<section><h2>きょうの1件<small>RANDOM</small></h2><div class="card"><p style="margin-top:0">どれから読めばいいか分からない人へ。これまでの議案から1件えらびます。</p>
<div id="pick" class="note">まだ、えらんでいません</div><p style="margin-bottom:0"><button class="btn" id="pickbtn">1件えらぶ</button></p></div></section>
<section><h2>最近決まったこと<small>LATEST</small></h2><div class="list">{"".join(item_card(i) for i in latest)}</div>
<p><a href="s/{latest_decided["id"]}.html">{E(latest_decided["name"])}をすべて見る →</a></p></section>
<section id="find"><h2>分野で探す<small>FIND</small></h2><div class="grid2">{cat_tiles}</div>
<h3 class="kindh">地域で探す</h3><div class="chips">{top_areas}<a class="chip" href="area/index.html">すべての地域 →</a></div></section>
<section id="sessions"><h2>会期ごとの一覧<small>SESSIONS</small></h2><div class="list">{sess_list}</div></section>
<script>
const P={json.dumps(pick_pool, ensure_ascii=False)};
const esc=s=>String(s).replace(/[&<>"']/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}})[c]);
document.getElementById('pickbtn').onclick=()=>{{const d=P[Math.floor(Math.random()*P.length)];
document.getElementById('pick').innerHTML='<a class="item" href="'+esc(d.u)+'"><div class="meta"><span>'+esc(d.s)+'</span></div><div class="hl">'+esc(d.h)+'</div></a>';}};
</script>"""
    write("index.html", page(SITE_NAME, body))
    nf = page("ページが見つかりません", '<h1>ページが見つかりません</h1><p>URLが変わったか、ページがなくなった可能性があります。</p><p><a href="index.html">ホームへ</a></p>')
    if SITE_URL:  # 404 はどの階層でも表示されるので、基準URLを固定する
        nf = nf.replace("<head>", f'<head><base href="{SITE_URL}">', 1)
    write("404.html", nf)
    if SITE_URL:
        urls = "".join(f"<url><loc>{SITE_URL}{urllib.parse.quote(p)}</loc></url>" for p in WRITTEN)
        (OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>', encoding="utf-8")
        (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n", encoding="utf-8")
    print(f"built: {len(sessions)} sessions, {len(items)} items, {len(explained)} explained -> {OUT}")


if __name__ == "__main__":
    build()
