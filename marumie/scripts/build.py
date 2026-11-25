"""data/*.json → docs/data.js（サイト本体 docs/index.html・app.js・style.css は手書き）"""
import json, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
data = {
    "budget": json.loads((ROOT / "data/budget.json").read_text()),
    "seimu": json.loads((ROOT / "data/seimu.json").read_text()),
    "built": datetime.date.today().isoformat(),
}
(ROOT / "docs/data.js").write_text("window.DATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")
print("docs/data.js を書き出しました")
