# やさしい大田区議会（非公式）

大田区議会で決まったことを、ふだんの言葉でまとめる静的サイト。
大田区・大田区議会の公式サイトではありません。

## しくみ

1. GitHub Actions が毎朝 6:30（日本時間）に `scripts/fetch.py` を実行し、大田区議会HP「本会議」の最新年の会期ページ（区長提出議案・議員提出議案・委員会提出議案・同意・請願陳情・報告・各会派の態度）を読みに行く。過去の年は `data/sessions/` に保存済みのものを使い、区のサーバーには取りに行かない（取得は1秒以上の間隔）
2. 取得結果を `data/sessions/*.json` としてリポジトリに残す
3. `scripts/build.py` が `data/sessions` と `data/summaries` から `site/` に静的HTMLを作る
4. GitHub Pages に公開する

## やさしい説明（data/summaries）

- 書き方の決まりは `prompts/summary-rules.md`（資料にないことは足さない）
- `basis: "doc"` … 議案書をもとにした説明（要点・金額つき）
- `basis: "title"` … 区のサイトから議案書が消えていて手に入らなかった議案。件名だけを言い換えた見出し
- 説明がない議案は、build.py が件名を機械的に言い換えて表示する
- 新しい会期の議案は自動では説明がつかない。議案書PDFを読んで `data/summaries/<会期id>.json` を足す
- `data/archived_pdfs.json` … Internet Archive に残っていた過去の議案書へのリンク

## 手元で動かす

```bash
python3 scripts/fetch.py
python3 scripts/build.py
python3 -m http.server 8765 -d site
```

サイト名は `scripts/build.py` 冒頭の `SITE_NAME`。公開URLは環境変数 `SITE_URL`（GitHub Actions では自動）。

## 公開（GitHub Pages）

1. GitHub に公開リポジトリを作り、このフォルダを push する
2. リポジトリの Settings → Pages → Source を「GitHub Actions」にする
3. Actions タブで `update-and-deploy` を手動実行（以後は毎朝自動）

## データの出どころ

- 大田区議会「本会議」 https://www.city.ota.tokyo.jp/gikai/kugikai_katsudou/honkaigi/index.html
- 同「意見が異なった議案に対する各会派の態度」（各会期ページ内）
- 各議案の議案書PDF、および Internet Archive に保存されている過去の議案書
