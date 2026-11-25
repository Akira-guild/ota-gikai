(() => {
  const D = window.DATA;
  const $ = (s) => document.querySelector(s);
  const sum = (a, f = (x) => x.value) => a.reduce((s, x) => s + f(x), 0);
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const pct = (v, t) => (t ? (v / t) * 100 : 0);
  const pctS = (v, t) => { const p = pct(v, t); return p < 1 && p > 0 ? "1%未満" : Math.round(p) + "%"; };

  // 金額表示
  function yen(v) {
    if (v >= 1e8) {
      const oku = Math.floor(v / 1e8), man = Math.round((v % 1e8) / 1e4);
      return oku.toLocaleString() + "億" + (man ? man.toLocaleString() + "万" : "") + "円";
    }
    if (v >= 1e4) return Math.round(v / 1e4).toLocaleString() + "万円";
    return v.toLocaleString() + "円";
  }
  function yenShort(v) {
    if (v >= 1e10) return Math.round(v / 1e8).toLocaleString() + "億円";
    if (v >= 1e8) return (v / 1e8).toFixed(1).replace(/\.0$/, "") + "億円";
    if (v >= 1e4) return Math.round(v / 1e4).toLocaleString() + "万円";
    return v.toLocaleString() + "円";
  }
  function yenHTML(v) {
    const s = v >= 1e10 ? yenShort(v) : yen(v);
    return s.replace(/(億|万|円)/g, (m) => `<small>${m}</small>`);
  }
  const card = (k, v, s, c) => `<div class="card" style="--c:var(${c})"><p class="k">${k}</p><p class="v">${v}</p>${s ? `<p class="s">${s}</p>` : ""}</div>`;

  // ツールチップ
  const tip = $("#tip");
  function showTip(e, html) { tip.innerHTML = html; tip.hidden = false; moveTip(e); }
  function moveTip(e) {
    const x = Math.min(e.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
    tip.style.left = x + "px"; tip.style.top = (e.clientY + 14) + "px";
  }
  const hideTip = () => { tip.hidden = true; };

  // ---------- サンキー図（自前SVG） ----------
  // opt: {left:[{label,value,color,desc}], center:{label,value,color}, right:[...]}
  function sankey(el, opt) {
    const { left, center, right } = opt;
    const W = 860, bw = 14, gap = 6, padT = 52, padB = 12, row = 34;
    const n = Math.max(left.length, right.length);
    const H = Math.max(320, n * row + padT + padB);
    const avail = H - padT - padB;
    const totL = sum(left), totR = sum(right);
    const k = Math.min((avail - gap * (left.length - 1)) / totL, (avail - gap * (right.length - 1)) / totR);
    const xL = 230, xR = W - 230 - bw, xC = (W - bw) / 2;
    const NS = "http://www.w3.org/2000/svg";

    const place = (nodes) => {
      const hs = nodes.map((d) => Math.max(d.value * k, 1.5));
      const h = hs.reduce((a, b) => a + b, 0) + gap * (nodes.length - 1);
      let y = padT + (avail - h) / 2;
      nodes.forEach((d, i) => { d.y = y; d.h = hs[i]; y += hs[i] + gap; });
    };
    place(left); place(right);
    const hC = Math.max(totL, totR) * k, yC = padT + (avail - hC) / 2;

    // ラベル位置（重なり回避）
    const labelYs = (nodes) => {
      const ys = nodes.map((d) => d.y + d.h / 2), min = 32;
      for (let i = 1; i < ys.length; i++) ys[i] = Math.max(ys[i], ys[i - 1] + min);
      const maxY = H - 14;
      if (ys[ys.length - 1] > maxY) {
        ys[ys.length - 1] = maxY;
        for (let i = ys.length - 2; i >= 0; i--) ys[i] = Math.min(ys[i], ys[i + 1] - min);
      }
      return ys;
    };

    let s = `<svg class="sk" viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${esc(opt.aria || "お金の流れのサンキー図")}">`;
    const total = center.value;
    const curve = (x1, y1t, y1b, x2, y2t, y2b) => {
      const m = (x1 + x2) / 2;
      return `M${x1},${y1t}C${m},${y1t} ${m},${y2t} ${x2},${y2t}L${x2},${y2b}C${m},${y2b} ${m},${y1b} ${x1},${y1b}Z`;
    };
    let acc = 0;
    left.forEach((d, i) => {
      const h = d.value * k;
      s += `<path class="lnk" data-side="L" data-i="${i}" fill="${d.color}" d="${curve(xL + bw, d.y, d.y + h, xC, yC + acc, yC + acc + h)}"/>`;
      acc += h;
    });
    acc = 0;
    right.forEach((d, i) => {
      const h = d.value * k;
      s += `<path class="lnk" data-side="R" data-i="${i}" fill="${d.color}" d="${curve(xC + bw, yC + acc, yC + acc + h, xR, d.y, d.y + h)}"/>`;
      acc += h;
    });
    left.forEach((d, i) => { s += `<rect class="node" data-side="L" data-i="${i}" x="${xL}" y="${d.y}" width="${bw}" height="${d.h}" rx="2" fill="${d.color}"/>`; });
    right.forEach((d, i) => { s += `<rect class="node" data-side="R" data-i="${i}" x="${xR}" y="${d.y}" width="${bw}" height="${d.h}" rx="2" fill="${d.color}"/>`; });
    s += `<rect x="${xC}" y="${yC}" width="${bw}" height="${hC}" rx="2" fill="${center.color}"/>`;

    const trunc = (t, m) => (t.length > m ? t.slice(0, m - 1) + "…" : t);
    const lys = labelYs(left), rys = labelYs(right);
    left.forEach((d, i) => {
      s += `<text x="${xL - 8}" y="${lys[i] - 3}" text-anchor="end" class="lbl">${esc(trunc(d.label, 15))}</text>`;
      s += `<text x="${xL - 8}" y="${lys[i] + 11}" text-anchor="end" class="amt">${yenShort(d.value)}・${pctS(d.value, total)}</text>`;
    });
    right.forEach((d, i) => {
      s += `<text x="${xR + bw + 8}" y="${rys[i] - 3}" class="lbl">${esc(trunc(d.label, 15))}</text>`;
      s += `<text x="${xR + bw + 8}" y="${rys[i] + 11}" class="amt">${yenShort(d.value)}・${pctS(d.value, total)}</text>`;
    });
    s += `<text x="${xC + bw / 2}" y="${yC - 24}" text-anchor="middle" class="ctr">${esc(center.label)}</text>`;
    s += `<text x="${xC + bw / 2}" y="${yC - 8}" text-anchor="middle" class="amt">${yen(center.value)}</text>`;
    s += `</svg>`;
    el.innerHTML = s;

    const svg = el.firstChild;
    const get = (t) => (t.dataset.side === "L" ? left : right)[+t.dataset.i];
    svg.addEventListener("mousemove", (e) => {
      const t = e.target;
      if (!t.dataset || !t.dataset.side) return hideTip();
      const d = get(t);
      svg.querySelectorAll(".lnk.hl").forEach((x) => x.classList.remove("hl"));
      svg.querySelector(`.lnk[data-side="${t.dataset.side}"][data-i="${t.dataset.i}"]`).classList.add("hl");
      showTip(e, `<b>${esc(d.label)}</b><br>${yen(d.value)}（${pctS(d.value, total)}）${d.desc ? `<br><span style="opacity:.8">${esc(d.desc)}</span>` : ""}`);
    });
    svg.addEventListener("mouseleave", () => { hideTip(); svg.querySelectorAll(".lnk.hl").forEach((x) => x.classList.remove("hl")); });
  }

  // 小さい項目を「その他」にまとめる
  function mergeSmall(items, total, th, color, label = "その他") {
    const big = items.filter((d) => d.value / total >= th);
    const small = items.filter((d) => d.value / total < th && d.value > 0);
    if (small.length > 1) big.push({ label, value: sum(small), color, desc: small.map((d) => d.label).join("・") });
    else big.push(...small);
    return big;
  }

  // ---------- 1. 区の予算 ----------
  const REV_DESC = {
    "特別区税": "区民税（住民税のうち区の分）・たばこ税など、区が直接集める税金",
    "特別区交付金": "固定資産税などを東京都が集め、23区で分け合うお金（都区財政調整）",
    "国庫支出金": "国から使い道を決めて来るお金（生活保護・児童手当・保育など）",
    "都支出金": "東京都から使い道を決めて来るお金",
    "地方消費税交付金": "消費税のうち地方の分として配られるお金",
    "繰入金": "区の貯金（基金）を取り崩したお金など",
    "特別区債": "区の借金（学校などの建設のため）",
    "使用料及び手数料": "施設の使用料、証明書の発行手数料など",
    "諸収入": "貸付金の返済、受託事業の収入、雑入など",
    "株式等譲渡所得割交付金": "株の売却益にかかる税のうち区に配られる分",
    "財産収入": "区の土地・建物の貸付料や基金の利子など",
    "配当割交付金": "株の配当にかかる税のうち区に配られる分",
    "繰越金": "前の年度に使い残したお金",
    "地方譲与税": "国が集めた税（自動車重量税・航空機燃料税など）の一部",
    "利子割交付金": "預金の利子にかかる税のうち区に配られる分",
    "地方特例交付金": "国の減税で減った分を国が補うお金",
    "分担金及び負担金": "保育料など、サービスを受ける人が負担するお金",
    "寄附金": "ふるさと納税など、区への寄附",
  };
  const EXP_DESC = {
    "福祉費": "子ども・高齢者・障害のある人への支援、生活保護など",
    "教育費": "小学校・中学校、図書館、生涯学習など",
    "総務費": "区役所の運営、地域・文化・スポーツ、税の徴収、選挙など",
    "土木費": "道路・橋・公園・河川",
    "環境清掃費": "ごみの収集・リサイクル、環境保全",
    "衛生費": "健康診断・予防接種・保健所など",
    "都市整備費": "まちづくり・住宅・建築",
    "産業経済費": "中小企業・商店街・ものづくり・観光の支援",
    "公債費": "区の借金の返済と利子",
    "議会費": "区議会の運営（議員報酬、政務活動費など）",
    "諸支出金": "基金への積立など",
    "予備費": "予想外の支出に備えるお金",
  };
  let bYear = D.budget[0].year, bLevel = "kan";

  function renderBudgetYears() {
    $("#budget-year").innerHTML = D.budget.map((b) => `<button data-v="${b.year}" class="${b.year === bYear ? "on" : ""}">${b.year}年度</button>`).join("");
  }
  function renderBudget() {
    const b = D.budget.find((x) => x.year === bYear);
    const T = b.total, G = css("--kusu"), U = css("--ume"), INK = css("--ink"), MUT = css("--muted");
    const rev = [...b.revenue].sort((a, c) => c.amount - a.amount);
    const exp = [...b.expenditure].sort((a, c) => c.amount - a.amount);
    const kuzei = b.revenue.find((r) => r.name === "特別区税");
    const top = exp[0];
    const gikai = b.expenditure.find((r) => r.name === "議会費");
    $("#budget-cards").innerHTML =
      card("一般会計の総額", yenHTML(T), b.label, "--ink") +
      card("いちばん大きな使い道", `${top.name} <small>${pctS(top.amount, T)}</small>`, yen(top.amount), "--ume") +
      card("区の税金でまかなう割合", `${pctS(kuzei.amount, T)}`, `特別区税 ${yen(kuzei.amount)}`, "--kusu") +
      card("区議会にかかるお金", yenHTML(gikai.amount), `議会費・総額の${pctS(gikai.amount, T)}`, "--sora");

    let left, right;
    if (bLevel === "kan") {
      left = mergeSmall(rev.map((r) => ({ label: r.name, value: r.amount, color: G, desc: REV_DESC[r.name] })), T, 0.01, G);
      right = mergeSmall(exp.map((r) => ({ label: r.name, value: r.amount, color: U, desc: EXP_DESC[r.name] })), T, 0.005, U);
    } else {
      const flat = (arr, c) => arr.flatMap((r) => r.items.map((i) => ({ label: i.name === r.name ? i.name : i.name, value: i.amount, color: c, desc: `${r.name}のうち` }))).sort((a, c) => c.value - a.value);
      left = mergeSmall(flat(rev, G), T, 0.008, G);
      right = mergeSmall(flat(exp, U), T, 0.004, U);
    }
    sankey($("#budget-sankey"), { left, right, center: { label: "一般会計", value: T, color: INK }, aria: "大田区一般会計予算の歳入から歳出へのサンキー図" });

    const list = (arr, desc, c) => arr.map((r) => `<li><span class="n">${esc(r.name)}</span><span class="a">${yenShort(r.amount)} <small style="color:${MUT}">${pctS(r.amount, T)}</small></span><span class="bar" style="--c:var(${c})"><i style="width:${Math.max(pct(r.amount, rev[0].amount > exp[0].amount ? rev[0].amount : exp[0].amount), 0.4)}%"></i></span>${desc[r.name] ? `<span class="d">${esc(desc[r.name])}</span>` : ""}</li>`).join("");
    $("#budget-rev-list").innerHTML = list(rev.filter((r) => r.amount >= 1e6), REV_DESC, "--kusu");
    $("#budget-exp-list").innerHTML = list(exp, EXP_DESC, "--ume") + `<li><span class="d">政務活動費は、この「議会費」の中から会派に交付されています。</span></li>`;
  }
  $("#budget-year").addEventListener("click", (e) => { if (e.target.dataset.v) { bYear = e.target.dataset.v; renderBudgetYears(); renderBudget(); } });
  $("#budget-level").addEventListener("click", (e) => {
    if (!e.target.dataset.v) return;
    bLevel = e.target.dataset.v;
    $("#budget-level").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x.dataset.v === bLevel));
    renderBudget();
  });

  // ---------- 2. 政務活動費 ----------
  const CAT_DESC = {
    "調査研究費": "視察・調査にかかる交通費や委託費など",
    "研修費": "研修会・講演会への参加費など",
    "広報費": "活動報告（区政レポート）の印刷・配布など",
    "広聴費": "区民の意見を聞く会の開催など",
    "要請・陳情活動費": "国や都などへの要請に行く交通費など",
    "会議費": "会派の会議の会場費など",
    "資料作成費": "調査資料の作成・印刷など",
    "資料購入費": "本・新聞・雑誌の購入など",
    "人件費": "活動を手伝うスタッフの給料",
    "事務所費": "活動のための事務所の家賃・光熱費など",
  };
  const S = D.seimu;
  let sYear = S[0].year, sKaiha = null;
  const fyLabel = (y) => `令和${+y - 2018}年度`;
  const ret = (k) => Math.max(k.income - k.spent, 0);
  const over = (k) => Math.max(k.spent - k.income, 0);

  function renderSeimuYears() {
    $("#seimu-year").innerHTML = S.map((y) => `<button data-v="${y.year}" class="${y.year === sYear ? "on" : ""}">${fyLabel(y.year)}</button>`).join("");
  }
  function renderSeimu() {
    const y = S.find((x) => x.year === sYear);
    const U = css("--ume"), G = css("--kusu"), B = css("--sora"), INK = css("--ink"), MUT = css("--muted");
    const K = y.kaiha.filter((k) => k.income > 0 || k.spent > 0);
    const R = sum(K, ret), O = sum(K, over), I = y.total.income, SP = y.total.spent;
    $("#seimu-cards").innerHTML =
      card("交付された額", yenHTML(I), `${y.label}・${y.total.members}人`, "--kusu") +
      card("使った額", yenHTML(SP), `交付額の${pctS(SP, I)}`, "--ume") +
      card("区に返した額", yenHTML(R), "使い残して返還", "--sora") +
      card("会派の自己負担", yenHTML(O), "交付額を超えて使った分", "--ink");

    const left = K.filter((k) => k.income > 0).sort((a, b) => b.income - a.income).map((k) => ({ label: k.name, value: k.income, color: G, desc: `${k.members}人の会派` }));
    if (O > 0) left.push({ label: "会派の自己負担", value: O, color: MUT, desc: "交付額を超えて使い、会派が自分で払った分" });
    const cats = y.categories.map((c) => ({ label: c, value: y.total.expenses[c], color: U, desc: CAT_DESC[c] })).sort((a, b) => b.value - a.value);
    const right = mergeSmall(cats, I + O, 0.01, U);
    right.push({ label: "区へ返還", value: R, color: B, desc: "使わずに区に返したお金" });
    sankey($("#seimu-sankey"), { left, right, center: { label: "政務活動費", value: I + O, color: INK }, aria: "政務活動費の会派から使い道へのサンキー図" });

    // chips
    const sorted = [...K].sort((a, b) => b.income - a.income);
    if (!sKaiha || !sorted.find((k) => k.name === sKaiha)) sKaiha = sorted[0].name;
    $("#kaiha-chips").innerHTML = sorted.map((k) => `<button class="chip ${k.name === sKaiha ? "on" : ""}" data-v="${esc(k.name)}">${esc(k.name)}<span>${k.members}人</span></button>`).join("");
    renderKaiha(y);

    // table
    const head = `<tr><th>会派</th><th>人数</th>${y.categories.map((c) => `<th>${esc(c)}</th>`).join("")}<th>支出計</th><th>交付額</th><th>返還／自己負担</th></tr>`;
    const rowH = (k, isT) => {
      const cells = y.categories.map((c) => {
        const v = k.expenses[c], p = pct(v, k.spent);
        const bg = `color-mix(in srgb, ${U} ${Math.min(p * 1.6, 85).toFixed(0)}%, transparent)`;
        return `<td class="cell" style="background:${bg}" title="${esc(c)} ${yen(v)}">${v ? Math.round(p) + "%" : "–"}</td>`;
      }).join("");
      const r = ret(k), o = over(k);
      return `<tr class="${isT ? "total" : ""}"><td title="${esc(k.name)}">${esc(k.name)}</td><td>${k.members}</td>${cells}<td>${yenShort(k.spent)}</td><td>${yenShort(k.income)}</td><td>${o ? `<span class="pill over">負担 ${yenShort(o)}</span>` : `<span class="pill ret">返還 ${yenShort(r)}</span>`}</td></tr>`;
    };
    $("#seimu-table").innerHTML = `<thead>${head}</thead><tbody>${sorted.map((k) => rowH(k)).join("")}${rowH({ ...y.total, name: "合計" }, true).replace(/<span class="pill.*?<\/span>/, `<span class="pill ret">返還 ${yenShort(R)}</span>`)}</tbody>`;

    $("#seimu-cats").innerHTML = y.categories.map((c) => `<dt>${esc(c)}</dt><dd>${esc(CAT_DESC[c] || "")}</dd>`).join("");
  }

  function renderKaiha(y) {
    const k = y.kaiha.find((x) => x.name === sKaiha);
    const U = css("--ume"), G = css("--kusu"), B = css("--sora"), INK = css("--ink"), MUT = css("--muted");
    const r = ret(k), o = over(k);
    const left = [];
    if (k.income) left.push({ label: "政務活動費の交付", value: k.income, color: G });
    if (o) left.push({ label: "会派の自己負担", value: o, color: MUT });
    const cats = y.categories.filter((c) => k.expenses[c] > 0).map((c) => ({ label: c, value: k.expenses[c], color: U, desc: CAT_DESC[c] })).sort((a, b) => b.value - a.value);
    const right = [...cats];
    if (r) right.push({ label: "区へ返還", value: r, color: B });
    $("#kaiha-detail").innerHTML = `
      <div class="kd-head"><h3>${esc(k.name)}</h3>
        <div class="kd-stats"><span>人数 <b>${k.members}人</b></span><span>交付 <b>${yen(k.income)}</b></span><span>支出 <b>${yen(k.spent)}</b></span>
        ${o ? `<span class="pill over">自己負担 ${yen(o)}</span>` : `<span class="pill ret">返還 ${yen(r)}</span>`}</div></div>
      ${k.note ? `<p class="kd-note">${esc(k.note)}</p>` : ""}
      <div class="chart-scroll"><div class="kd-chart"></div></div>`;
    if (sum(left) > 0) sankey($("#kaiha-detail .kd-chart"), { left, right, center: { label: k.name.length > 12 ? k.name.slice(0, 11) + "…" : k.name, value: k.income + o, color: INK }, aria: `${k.name}の政務活動費の使い道` });
  }

  function renderTrend() {
    const G = css("--kusu"), U = css("--ume"), B = css("--sora");
    const ys = [...S].sort((a, b) => a.year - b.year);
    const W = 480, H = 230, padL = 44, padB = 28, padT = 26;
    const max = Math.max(...ys.map((y) => y.total.income)) * 1.08;
    const gw = (W - padL) / ys.length, bw = Math.min(22, gw / 4.5);
    let s = `<svg class="trend" viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="政務活動費の年度ごとの推移">`;
    for (let i = 0; i <= 4; i++) {
      const v = (max / 4) * i, yy = H - padB - ((H - padB - padT) * i) / 4;
      s += `<line x1="${padL}" x2="${W}" y1="${yy}" y2="${yy}" stroke="currentColor" opacity=".12"/><text x="${padL - 6}" y="${yy + 4}" text-anchor="end">${Math.round(v / 1e6)}</text>`;
    }
    s += `<text x="4" y="12" style="font-size:11px">（百万円）</text>`;
    ys.forEach((y, i) => {
      const R = sum(y.kaiha, ret);
      const vals = [[y.total.income, G, "交付"], [y.total.spent, U, "使った額"], [R, B, "返還"]];
      const x0 = padL + gw * i + (gw - bw * 3 - 8) / 2;
      vals.forEach(([v, c, l], j) => {
        const h = ((H - padB - padT) * v) / max;
        s += `<rect x="${x0 + j * (bw + 4)}" y="${H - padB - h}" width="${bw}" height="${h}" rx="3" fill="${c}"><title>${fyLabel(y.year)} ${l} ${yen(v)}</title></rect>`;
      });
      s += `<text x="${padL + gw * i + gw / 2}" y="${H - 8}" text-anchor="middle">${fyLabel(y.year).replace("年度", "")}</text>`;
    });
    s += `</svg><div class="legend"><span><i style="background:${G}"></i>交付</span><span><i style="background:${U}"></i>使った額</span><span><i style="background:${B}"></i>区へ返還</span></div><p class="note">令和5年度は改選のため5月〜3月の11か月分（4月分は別に公表）。</p>`;
    $("#seimu-trend").innerHTML = s;
  }

  $("#seimu-year").addEventListener("click", (e) => { if (e.target.dataset.v) { sYear = e.target.dataset.v; renderSeimuYears(); renderSeimu(); } });
  $("#kaiha-chips").addEventListener("click", (e) => {
    const b = e.target.closest(".chip"); if (!b) return;
    sKaiha = b.dataset.v;
    $("#kaiha-chips").querySelectorAll(".chip").forEach((x) => x.classList.toggle("on", x.dataset.v === sKaiha));
    renderKaiha(S.find((x) => x.year === sYear));
  });

  // ---------- 出典 ----------
  $("#sources").innerHTML =
    D.budget.map((b) => `<li>区の予算：大田区「${esc(b.label)} 各会計予算（議案）」第1表 歳入歳出予算（一般会計）<br><a href="${b.source}" target="_blank" rel="noopener">${esc(b.source)}</a></li>`).join("") +
    `<li>政務活動費：大田区議会「政務活動費収支一覧」（${S.map((y) => fyLabel(y.year)).join("・")}）<br><a href="https://www.city.ota.tokyo.jp/gikai/hirakareta_gikai/seimu-katsudouhi.html" target="_blank" rel="noopener">https://www.city.ota.tokyo.jp/gikai/hirakareta_gikai/seimu-katsudouhi.html</a></li>` +
    `<li>政務活動費の人数は各年度末時点。年度の途中で会派の人数が変わった場合、交付額は在籍した月数で計算されています。</li>`;
  $("#built").textContent = `データ更新：${D.built}`;

  const all = () => { renderBudgetYears(); renderBudget(); renderSeimuYears(); renderSeimu(); renderTrend(); };
  all();
  // ダークモード切替で色を塗り直す
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", all);
  let rt; addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(hideTip, 100); });
})();
