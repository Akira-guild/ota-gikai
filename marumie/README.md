# まる見え大田区（非公式）

大田区のお金の流れを、サンキー図で見える化する静的サイト。
チームみらい「まる見え政治資金」の見せ方を参考にした大田区版。大田区・大田区議会・チームみらいとは関係ありません。

## 載せているもの

1. **区の一般会計予算**（令和8年度当初予算）… 歳入の款 → 一般会計 → 歳出の款（「くわしく」で項まで）
2. **区議会の政務活動費**（令和4〜7年度）… 会派への交付 → 使い道10区分 ＋ 区へ返還。会派ごとの図、会派×使い道の表、年度推移

色は大田区モチーフ：梅（区の花）・クスノキ（区の木）・羽田の空・海苔。

## しくみ

```
raw/*.pdf ──parse_*.py──▶ data/*.json ──build.py──▶ docs/data.js
                                                    docs/index.html・app.js・style.css（手書き）
```

- `scripts/parse_seimu.py` … 「政務活動費収支一覧」PDF → `data/seimu.json`。各会派の内訳の合計＝支出合計、会派の合計＝区の示す合計 を検算
- `scripts/parse_budget.py` … 「各会計予算（議案）」第1表 → `data/budget.json`。款の合計＝総額、項の合計＝款 を検算（数字が `(cid:19)`〜`(cid:28)` で埋め込まれているのを復号）
- `scripts/build.py` … JSON を `docs/data.js` にまとめる（標準ライブラリのみ）
- サンキー図は外部ライブラリなしの自前SVG

## 手元で動かす

```bash
python3 -m venv .venv && .venv/bin/pip install pdfplumber
.venv/bin/python scripts/parse_seimu.py
.venv/bin/python scripts/parse_budget.py
python3 scripts/build.py
python3 -m http.server 8777 -d docs
```

## データを足すとき

- 政務活動費：新しい年度のPDFを `raw/` に置き、`parse_seimu.py` の `FILES` に1行足す
- 予算：新しい年度の「各会計予算（議案）」PDFを `raw/` に置き、`parse_budget.py` の `FILES` に1行足す
- 足したら `build.py` を実行し、`index.html` の `?v=` を上げる（キャッシュ対策）

## 公開

https://akira-guild.github.io/marumie-ota/

GitHub Pages の配信元は `main` ブランチの `/docs`。`build.py` で作った `docs/data.js` もコミットしておく（ビルドは手元で行う）。

## 出典

- 大田区「令和8年度 各会計予算（議案）」 https://www.city.ota.tokyo.jp/kuseijoho/suuji/yosan_kessan/yosan/r08yosan/r08-yosan.html
- 大田区議会「政務活動費収支一覧」 https://www.city.ota.tokyo.jp/gikai/hirakareta_gikai/seimu-katsudouhi.html
