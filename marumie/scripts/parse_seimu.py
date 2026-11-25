"""大田区議会「政務活動費収支一覧」PDF → data/seimu.json
使い方: python scripts/parse_seimu.py   （pdfplumber が必要）"""
import json, re, pathlib, pdfplumber

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://www.city.ota.tokyo.jp/gikai/hirakareta_gikai/seimu-katsudouhi.files/"
FILES = [  # (年度ラベル, 期間, ファイル)
    ("2025", "令和7年度（2025年4月〜2026年3月）", "r7seimukatsudo.pdf"),
    ("2024", "令和6年度（2024年4月〜2025年3月）", "r6seimukatsudo.pdf.pdf"),
    ("2023", "令和5年度（2023年5月〜2024年3月）", "r5.5-r6.3seimukatsudo.pdf"),
    ("2022", "令和4年度（2022年4月〜2023年3月）", "r4seimukatsudo.pdf"),
]
num = lambda s: int(re.sub(r"[^\d]", "", s or "") or 0)

out = []
for year, label, fn in FILES:
    with pdfplumber.open(ROOT / "raw" / fn) as pdf:
        rows, cats, text = [], None, ""
        for pg in pdf.pages:
            text += pg.extract_text() or ""
            for t in pg.extract_tables():
                for r in t:
                    cells = [(c or "").strip() for c in r]
                    if "調査研究費" in cells:
                        i = cells.index("調査研究費")
                        cats = [c.replace(" ", "").replace("\n", "") for c in cells[i:] if c]
                    elif cats and cells[0] and re.search(r"\d", cells[1] or ""):
                        rows.append(cells)
    kaiha, total = [], None
    for c in rows:
        name_lines = c[0].split("\n")
        name = "".join(l for l in name_lines if not l.startswith(("（", "(")))
        name = re.sub(r"※\d", "", name).replace(" ", "").strip()
        note = " ".join(l for l in name_lines if l.startswith(("（", "(")))
        members = num(c[1].split("\n")[0])
        vals = [num(x) for x in c[2:2 + len(cats) + 2]]
        rec = {"name": name, "note": note, "members": members, "income": vals[0],
               "expenses": dict(zip(cats, vals[1:1 + len(cats)])), "spent": vals[1 + len(cats)]}
        assert sum(rec["expenses"].values()) == rec["spent"], (year, name)
        if name.startswith("合計"):
            total = rec
        else:
            kaiha.append(rec)
    assert total and sum(k["income"] for k in kaiha) == total["income"], year
    m = re.search(r"月額(\d+)万円", text)
    out.append({"year": year, "label": label, "source": BASE + fn,
                "monthly_per_member": int(m.group(1)) * 10000 if m else None,
                "categories": cats, "kaiha": kaiha, "total": total})
    print(year, len(kaiha), "会派", total["income"], total["spent"])

(ROOT / "data" / "seimu.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
