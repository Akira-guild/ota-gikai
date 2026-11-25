"""大田区議会の本会議ページ（定例会・臨時会ごと）から議決結果を集めて data/sessions/*.json に保存する。"""
import html, json, re, time, pathlib, urllib.request, urllib.parse, sys

BASE = "https://www.city.ota.tokyo.jp"
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"; OUT = ROOT / "data" / "sessions"
RAW.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (gikai-wakaru-ota; static site builder)"

def get(path, refresh=False):
    url = urllib.parse.urljoin(BASE, path)
    key = RAW / (re.sub(r"[^A-Za-z0-9_.-]", "_", urllib.parse.urlparse(url).path.strip("/")))
    if key.exists() and not refresh:
        return key.read_text(encoding="utf-8"), url
    time.sleep(1.0)  # 区のサーバーに負担をかけない
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    body = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    key.write_text(body, encoding="utf-8")
    return body, url

def clean(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("　", " ")
    return "\n".join(l.strip() for l in s.splitlines() if l.strip())

def main_part(h):
    i = h.find("本文ここから"); j = h.find("このページについて")
    return h[i if i >= 0 else 0: j if j > 0 else len(h)]

def tables(h):
    out = []
    for t in re.findall(r"<table.*?</table>", h, re.S):
        rows = []
        for tr in re.findall(r"<tr.*?</tr>", t, re.S):
            cells = [clean(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S)]
            if cells: rows.append(cells)
        if rows: out.append(rows)
    return out

def pdfs(h, page_url):
    return [{"label": clean(t), "url": urllib.parse.urljoin(page_url, u)}
            for u, t in re.findall(r'<a[^>]+href="([^"]+\.pdf)"[^>]*>(.*?)</a>', h, re.S)]

KIND = [("態度", "taido"), ("区長提出", "kucho"), ("議員提出", "giin"), ("委員会提出", "iinkai"),
        ("請願", "seichin"), ("陳情", "seichin"), ("同意", "doi"), ("人事", "doi"), ("報告", "hokoku")]

def kind_of(title):
    for k, v in KIND:
        if k in title: return v
    return "other"

def norm_head(c):
    c = c.replace("\n", "").replace(" ", "")
    for k, v in [("番号", "no"), ("件名", "title"), ("議決日", "date"), ("議決内容", "result"), ("結果", "result"),
                 ("付託委員会", "committee"), ("付託日", "referred"), ("委員会", "committee")]:
        if k in c: return v
    return c

def parse_page(path):
    h, url = get(path)
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    title = clean(m.group(1)).split("：")[-1] if m else ""
    body = main_part(h)
    page = {"title": title, "kind": kind_of(title), "url": url, "pdfs": pdfs(body, url), "rows": []}
    for t in tables(body):
        head = t[0]
        if page["kind"] == "taido":
            factions = [c.replace("\n", "") for c in head[2:-1]]
            page["factions"] = factions
            for r in t[1:]:
                if len(r) < len(head): continue
                page["rows"].append({"no": r[0], "title": r[1],
                                     "votes": dict(zip(factions, r[2:-1])), "result": r[-1]})
        else:
            keys = [norm_head(c) for c in head]
            for r in t[1:]:
                if len(r) != len(keys): continue
                page["rows"].append(dict(zip(keys, r)))
    return page

def sessions():
    h, _ = get("/gikai/kugikai_katsudou/honkaigi/index.html", refresh=True)
    seen = []
    for m in re.finditer(r'href="(/gikai/kugikai_katsudou/honkaigi/r_(\d+)/(\d)(teirei|rinji)/index.html)"', h):
        if m.group(1) not in [s[0] for s in seen]:
            seen.append((m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)))
    return seen

def main():
    only = sys.argv[1:]
    all_s = sessions()
    max_era = max(e for _, e, _, _ in all_s)
    for path, era, n, typ in all_s:
        sid = f"r{era:02d}-{n}{'t' if typ == 'teirei' else 'r'}"
        if only and sid not in only: continue
        latest = era >= max_era  # 最新年は毎回取り直す
        if not latest and (OUT / f"{sid}.json").exists() and not only:
            continue  # 過去の会期は保存済みのデータを使い、区のサーバーに取りに行かない
        h, url = get(path, refresh=latest)
        body = main_part(h)
        links = []
        for u in re.findall(r'href="([^"]+\.html)"', body):
            full = urllib.parse.urljoin(url, u)
            p = urllib.parse.urlparse(full).path
            if p.startswith(path.rsplit("/", 1)[0] + "/") and not p.endswith("index.html") and p not in links:
                links.append(p)
        pages = []
        for p in links:
            try:
                if latest: get(p, refresh=True)
                pages.append(parse_page(p))
            except Exception as e:
                print("  skip", p, e, file=sys.stderr)
        name = f"令和{era}年第{n}回{'定例会' if typ == 'teirei' else '臨時会'}"
        data = {"id": sid, "name": name, "era": era, "n": n, "type": typ, "url": url, "pages": pages}
        (OUT / f"{sid}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(sid, name, sum(len(p["rows"]) for p in pages), "rows")

if __name__ == "__main__":
    main()
