"""大田区「各会計予算（議案）」PDF の第1表（歳入歳出予算・一般会計）→ data/budget.json
使い方: python scripts/parse_budget.py   （pdfplumber が必要）"""
import json, re, pathlib, pdfplumber

ROOT = pathlib.Path(__file__).resolve().parent.parent
FILES = [("2026", "令和8年度（2026年度）当初予算",
          "https://www.city.ota.tokyo.jp/kuseijoho/suuji/yosan_kessan/yosan/r08yosan/r08-yosan.files/01_r8_yosan.pdf",
          "r08_yosan.pdf")]

def decode(t):
    # 埋め込みフォントの数字が (cid:19)〜(cid:28) = 0〜9、(cid:15)=","、(cid:3)=空白 で出てくる
    t = re.sub(r"\(cid:(\d+)\)", lambda m: {"15": ",", "3": " ", "16": "-"}.get(m.group(1),
               str(int(m.group(1)) - 19) if 19 <= int(m.group(1)) <= 28 else ""), t)
    return t

ITEM = re.compile(r"(\d{1,2}) ((?:[^\d\s,]+ ?)+?)( +)([\d,]+)(?=\s|$)")

def parse_page(text):
    left, right = [], []
    for line in text.split("\n"):
        ms = list(ITEM.finditer(line))
        for i, m in enumerate(ms):
            kind = "kan" if len(m.group(3)) >= 4 else "kou"
            rec = (kind, int(m.group(1)), m.group(2).replace(" ", ""), int(m.group(4).replace(",", "")))
            (left if i == 0 else right).append(rec)
    kans = []
    for kind, no, name, amt in left + right:
        if kind == "kan":
            kans.append({"no": no, "name": name, "amount": amt * 1000, "items": []})
        elif kans:
            kans[-1]["items"].append({"no": no, "name": name, "amount": amt * 1000})
    return kans

out = []
for year, label, url, fn in FILES:
    with pdfplumber.open(ROOT / "raw" / fn) as pdf:
        pages = [decode(p.extract_text() or "") for p in pdf.pages]
    rev_page = next(p for p in pages if "１ 歳 入" in p and "第 １ 表" in p)
    exp_page = next(p for p in pages if "２ 歳 出" in p and "款 項" in p)
    total = int(re.search(r"歳 入 合 計\s+([\d,]+)", rev_page).group(1).replace(",", "")) * 1000
    rev, exp = parse_page(rev_page), parse_page(exp_page)
    for side, kans in (("歳入", rev), ("歳出", exp)):
        assert sum(k["amount"] for k in kans) == total, (side, sum(k["amount"] for k in kans), total)
        for k in kans:
            assert sum(i["amount"] for i in k["items"]) == k["amount"], (side, k["name"])
        print(side, len(kans), "款 OK")
    out.append({"year": year, "label": label, "source": url, "total": total, "revenue": rev, "expenditure": exp})

(ROOT / "data" / "budget.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
