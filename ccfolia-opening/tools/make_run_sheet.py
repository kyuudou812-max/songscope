"""本番で KP が横に開いておく「進行表」（run-sheet.local.html）を作る。

演出台本（DIRECTION.local.md）の表と、チャットパレット（PALETTES.local.md）の台詞を、話ごとのタブに並べる。
  - 表の「間」に「5秒」のような秒数があれば、押すと数え始めるボタンにする（間を頭で数えなくてよい）
  - 台詞は押すとコピーできる（チャットパレットが使えないときの予備。`\\n` は改行にしてコピー）
  - 済んだ行にはチェックを付けられる（このブラウザにだけ保存）
見た目は STYLE.md（黒地・明朝・温かい灰白）。どちらの .local.md もシナリオの文を含むので、出力も git の対象外。

使い方: python3 tools/make_run_sheet.py   → ccfolia-opening/run-sheet.local.html をブラウザで開く
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABS = [("1", "第一話"), ("2", "第二話"), ("3", "第三話"), ("4", "第四話"), ("5", "第五話"), ("6", "第六話"),
        ("7", "第七話"), ("8", "第八話"), ("9", "最終話"), ("all", "全話")]
KANJI = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8"}


def tab_of(title):
    m = re.search(r"第([一二三四五六七八])話", title)
    if m:
        return KANJI[m.group(1)]
    if "最終話" in title or "エンディング" in title:
        return "9"
    if "全話" in title or "本番前" in title:
        return "all"
    return None


def inline(s):
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def timers(s):
    """「5秒」「2秒ずつ」などを、押すと数えるボタンにする"""
    def rep(m):
        return f'<button class="t" data-s="{m.group(1)}">{m.group(0)}</button>'
    return re.sub(r"(\d+(?:\.\d+)?)秒", rep, s)


def sections(md):
    """見出しごとに区切る → [(見出し, 本文の行)]"""
    out, cur = [], None
    for line in md.splitlines():
        h = re.match(r"^(##+)\s+(.*)", line)
        if h:
            cur = [h.group(2), []]
            out.append(cur)
        elif cur:
            cur[1].append(line)
    return out


def render_body(lines, sid):
    parts, table, n = [], [], 0

    def flush():
        nonlocal table, n
        if not table:
            return
        rows = [r for r in table if not re.match(r"^\|\s*-", r)]
        head, body = rows[0], rows[1:]
        cells = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
        h = "".join(f"<th>{inline(c)}</th>" for c in cells(head))
        b = ""
        for r in body:
            n += 1
            key = f"{sid}-{n}"
            b += f'<tr><td class="ck"><input type="checkbox" id="c{key}" data-k="{key}"></td>' + "".join(
                f"<td>{timers(inline(c))}</td>" for c in cells(r)) + "</tr>"
        parts.append(f'<div class="tw"><table><thead><tr><th></th>{h}</tr></thead><tbody>{b}</tbody></table></div>')
        table = []

    for line in lines:
        if line.startswith("|"):
            table.append(line)
            continue
        flush()
        s = line.strip()
        if not s or s == "---":
            continue
        if s.startswith("- "):
            parts.append(f"<p class='li'>{timers(inline(s[2:]))}</p>")
        else:
            parts.append(f"<p>{timers(inline(s))}</p>")
    flush()
    return "".join(parts)


def palettes(md):
    """話ごとの台詞：[(ラベル, [台詞])]"""
    out, tab, label, block, inblock = {}, None, "", [], False
    for line in md.splitlines():
        h = re.match(r"^##\s+(.*)", line)
        if h:
            tab = tab_of(h.group(1)) or ("all" if "共通" in h.group(1) else None)
            continue
        if line.startswith("```"):
            if inblock and tab:
                out.setdefault(tab, []).append((label, block))
            inblock, block = not inblock, []
            continue
        if inblock:
            if line.strip():
                block.append(line)
        elif line.strip() and not line.startswith(("※", "|", "-", "#")):
            label = line.strip()
    return out


def main():
    d = (ROOT / "DIRECTION.local.md").read_text(encoding="utf-8")
    p = (ROOT / "PALETTES.local.md").read_text(encoding="utf-8")
    by_tab = {k: [] for k, _ in TABS}
    for i, (title, lines) in enumerate(sections(d)):
        k = tab_of(title)
        if k:
            by_tab[k].append(f'<section><h2>{inline(title)}</h2>{render_body(lines, f"s{i}")}</section>')
    pal = palettes(p)
    panes = []
    for k, name in TABS:
        lines_html = ""
        for label, block in pal.get(k, []):
            items = "".join(f'<button class="cp" data-x="{html.escape(json.dumps(x.replace(chr(92) + "n", chr(10)), ensure_ascii=False))}">'
                            f"{inline(x.replace(chr(92) + 'n', ' / '))}</button>" for x in block)
            lines_html += f"<h3>{inline(label)}</h3><div class='cps'>{items}</div>"
        panes.append(f'<div class="pane" id="p{k}" hidden><div class="cols"><div class="main">{"".join(by_tab[k])}</div>'
                     f'<aside><h2>台詞（押すとコピー）</h2>{lines_html or "<p>なし</p>"}</aside></div></div>')
    tabs = "".join(f'<button class="tab" data-k="{k}">{n}</button>' for k, n in TABS)
    page = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>進行表</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@500;700&display=swap">
<style>
:root {{ --ink:#040404; --paper:#120f0e; --raise:#1b1715; --line:#2e2724; --text:#e1dcd6; --quiet:#b9b1aa; --quietest:#8d857e; --lamp:#ecd6b8;
  --mincho:"Shippori Mincho","Hiragino Mincho ProN","Yu Mincho",serif; color-scheme:dark; }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--paper); color:var(--text); font-family:var(--mincho); line-height:1.7; font-size:15px }}
header {{ position:sticky; top:0; z-index:5; background:var(--ink); border-bottom:1px solid var(--line); padding:10px 16px; display:flex; gap:6px; flex-wrap:wrap; align-items:center }}
.tab {{ background:none; border:1px solid var(--line); color:var(--quiet); font:inherit; padding:4px 12px; cursor:pointer }}
.tab[aria-pressed=true] {{ color:var(--ink); background:var(--lamp); border-color:var(--lamp) }}
#timer {{ margin-left:auto; font-size:28px; min-width:5ch; text-align:right; color:var(--lamp); font-variant-numeric:tabular-nums }}
#timer.done {{ color:var(--quietest) }}
.cols {{ display:grid; grid-template-columns:minmax(0,1fr) 340px; gap:24px; padding:16px }}
@media (max-width:900px) {{ .cols {{ grid-template-columns:1fr }} }}
h2 {{ font-weight:500; font-size:1.1rem; letter-spacing:.08em; border-bottom:1px solid var(--line); padding-bottom:6px; margin:24px 0 10px }}
h3 {{ font-weight:500; font-size:.9rem; color:var(--lamp); margin:16px 0 6px }}
p {{ margin:6px 0; color:var(--quiet) }} p.li::before {{ content:"・"; color:var(--quietest) }}
.tw {{ overflow-x:auto }}
table {{ border-collapse:collapse; width:100%; font-size:.92rem }}
th, td {{ border-bottom:1px solid var(--line); padding:6px 8px; text-align:left; vertical-align:top }}
th {{ color:var(--quietest); font-weight:500 }}
tr:has(input:checked) td {{ color:var(--quietest) }}
td.ck {{ width:28px }} input {{ accent-color:#ecd6b8; width:18px; height:18px }}
code {{ color:var(--lamp); font-size:.85em }}
button.t {{ background:var(--raise); border:1px solid var(--lamp); color:var(--lamp); font:inherit; padding:0 6px; cursor:pointer }}
aside {{ position:sticky; top:64px; align-self:start; max-height:calc(100vh - 80px); overflow:auto }}
.cps {{ display:grid; gap:4px }}
.cp {{ text-align:left; background:var(--raise); border:1px solid var(--line); color:var(--text); font:inherit; padding:6px 8px; cursor:pointer }}
.cp:active, .cp.ok {{ border-color:var(--lamp) }}
button:focus-visible {{ outline:2px solid var(--lamp); outline-offset:2px }}
</style></head><body>
<header>{tabs}<span id="timer" class="done">—</span></header>
{"".join(panes)}
<script>
const $$ = (s, r=document) => [...r.querySelectorAll(s)];
function show(k) {{
  $$(".pane").forEach(p => p.hidden = p.id !== "p" + k);
  $$(".tab").forEach(b => b.setAttribute("aria-pressed", b.dataset.k === k));
  try {{ localStorage.setItem("tab", k); }} catch (e) {{}}
}}
$$(".tab").forEach(b => b.onclick = () => show(b.dataset.k));
let tm = null;
const T = document.getElementById("timer");
$$("button.t").forEach(b => b.onclick = () => {{
  clearInterval(tm);
  let end = Date.now() + parseFloat(b.dataset.s) * 1000;
  T.classList.remove("done");
  const tick = () => {{ const r = Math.max(0, (end - Date.now()) / 1000); T.textContent = r.toFixed(1);
    if (r <= 0) {{ clearInterval(tm); T.classList.add("done"); }} }};
  tick(); tm = setInterval(tick, 100);
}});
$$(".cp").forEach(b => b.onclick = async () => {{
  const x = JSON.parse(b.dataset.x);
  try {{ await navigator.clipboard.writeText(x); }} catch (e) {{
    const t = document.createElement("textarea"); t.value = x; document.body.append(t); t.select(); document.execCommand("copy"); t.remove(); }}
  b.classList.add("ok"); setTimeout(() => b.classList.remove("ok"), 600);
}});
$$("input[type=checkbox]").forEach(c => {{
  try {{ c.checked = localStorage.getItem("ck" + c.dataset.k) === "1"; }} catch (e) {{}}
  c.onchange = () => {{ try {{ localStorage.setItem("ck" + c.dataset.k, c.checked ? "1" : "0"); }} catch (e) {{}} }};
}});
let first = "1"; try {{ first = localStorage.getItem("tab") || "1"; }} catch (e) {{}}
show(first);
</script></body></html>"""
    out = ROOT / "run-sheet.local.html"
    out.write_text(page, encoding="utf-8")
    print(out, f"{out.stat().st_size / 1024:.0f}KB")


if __name__ == "__main__":
    main()
