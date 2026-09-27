"""SVG でアニメイラスト風のバストアップを描き、Chromium で画像にする（試し描き：加賀美ハヤト）。

使い方:
    python3 rofmao_svg.py <出力png>
"""
import math
import sys

from playwright.sync_api import sync_playwright

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

HAIR_TOP, HAIR_BOT, HAIR_LINE, HAIR_HI = "#cf9565", "#a8683f", "#7a4a30", "#f3cfa6"
SKIN, SKIN_SH, LINE = "#fff0e6", "#f3cbb6", "#8a5a48"


def lock(x0, y0, x1, y1, bend, w):
    """根元が太く、先がとがる毛束（二次ベジェ）"""
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    nx, ny = -dy / L, dx / L
    mx, my = (x0 + x1) / 2 + nx * bend, (y0 + y1) / 2 + ny * bend
    lx, ly = x0 + nx * w / 2, y0 + ny * w / 2
    rx, ry = x0 - nx * w / 2, y0 - ny * w / 2
    c1 = (mx + nx * w * 0.32, my + ny * w * 0.32)
    c2 = (mx - nx * w * 0.32, my - ny * w * 0.32)
    return (f"M{lx:.1f},{ly:.1f} Q{c1[0]:.1f},{c1[1]:.1f} {x1:.1f},{y1:.1f} "
            f"Q{c2[0]:.1f},{c2[1]:.1f} {rx:.1f},{ry:.1f} Z")


def eye(cx, s, expr, uid):
    """s=-1 が向かって左の目。外側の目尻を少し上げる。"""
    if expr == "laugh":
        return (f'<path d="M{cx - 24 * s},{342} Q{cx + 2 * s},{318} {cx + 26 * s},{338}" '
                f'fill="none" stroke="#3a2218" stroke-width="5" stroke-linecap="round"/>'
                f'<path d="M{cx + 26 * s},{338} l{6 * s},{2}" stroke="#3a2218" stroke-width="3" stroke-linecap="round"/>')
    low = 6 if expr == "serious" else 0
    white = (f"M{cx - 24 * s},{340} C{cx - 18 * s},{320 + low} {cx + 12 * s},{314 + low} {cx + 28 * s},{326 + low} "
             f"C{cx + 24 * s},{346} {cx + 10 * s},{357} {cx - 4 * s},{357} C{cx - 16 * s},{356} {cx - 22 * s},{348} "
             f"{cx - 24 * s},{340} Z")
    lash = (f"M{cx - 26 * s},{341} C{cx - 19 * s},{316 + low} {cx + 12 * s},{309 + low} {cx + 31 * s},{323 + low} "
            f"L{cx + 36 * s},{330 + low} L{cx + 28 * s},{329 + low} C{cx + 10 * s},{318 + low} {cx - 15 * s},{322 + low} "
            f"{cx - 22 * s},{343} Z")
    ix = cx + 2 * s
    return f'''
    <clipPath id="eyeclip{uid}"><path d="{white}"/></clipPath>
    <path d="{white}" fill="#ffffff"/>
    <g clip-path="url(#eyeclip{uid})">
      <ellipse cx="{ix}" cy="339" rx="14.5" ry="18.5" fill="url(#iris)"/>
      <ellipse cx="{ix}" cy="337" rx="6.5" ry="9.5" fill="#3b1e0e"/>
      <ellipse cx="{ix}" cy="339" rx="14.5" ry="18.5" fill="none" stroke="#5a3418" stroke-width="1.4"/>
      <ellipse cx="{cx + 4 * s}" cy="{318 + low}" rx="30" ry="9" fill="#6b4a3a" opacity="0.35" filter="url(#soft2)"/>
      <circle cx="{ix - 5 * s}" cy="{330 + low * 0.6}" r="4.8" fill="#fff"/>
      <circle cx="{ix + 6 * s}" cy="347" r="2.2" fill="#fff" opacity="0.9"/>
    </g>
    <path d="{lash}" fill="#3a2218"/>
    <path d="M{cx - 8 * s},{357.5} Q{cx + 10 * s},{357} {cx + 22 * s},{349}" fill="none" stroke="#9a6a58"
          stroke-width="1.3" stroke-linecap="round"/>
    <path d="M{cx - 12 * s},{311 + low} Q{cx + 8 * s},{305 + low} {cx + 24 * s},{315 + low}" fill="none"
          stroke="#c99a88" stroke-width="1.1" stroke-linecap="round"/>'''


def brow(cx, s, expr):
    if expr == "serious":
        return (f'<path d="M{cx - 22 * s},{302} Q{cx + 2 * s},{302} {cx + 24 * s},{295} L{cx + 24 * s},{298} '
                f'Q{cx + 2 * s},{306} {cx - 22 * s},{306} Z" fill="#8a5a3a"/>')
    y = -3 if expr == "laugh" else 0
    return (f'<path d="M{cx - 20 * s},{300 + y} Q{cx + 2 * s},{290 + y} {cx + 24 * s},{296 + y} L{cx + 24 * s},{298 + y} '
            f'Q{cx + 2 * s},{294 + y} {cx - 20 * s},{303 + y} Z" fill="#8a5a3a"/>')


def mouth(expr):
    if expr == "laugh":
        return '''<path d="M283,390 Q300,393 317,390 Q313,410 300,412 Q287,410 283,390 Z" fill="#b8404e" stroke="#7a3a36" stroke-width="1.4"/>
        <path d="M286,391 Q300,394 314,391 L313,396 Q300,398 287,396 Z" fill="#fff"/>
        <ellipse cx="300" cy="405" rx="7" ry="3.5" fill="#ef8a92"/>'''
    if expr == "serious":
        return '<path d="M290,396 Q300,394 310,396" fill="none" stroke="#9a5a50" stroke-width="1.8" stroke-linecap="round"/>'
    return '<path d="M290,392 Q300,398 310,392" fill="none" stroke="#9a5a50" stroke-width="1.8" stroke-linecap="round"/>'


BANG_L = ("M298,116 C262,128 226,164 218,214 C212,248 212,276 216,300 Q226,302 232,318 Q236,298 242,292 "
          "Q252,304 256,322 Q260,300 266,292 Q274,300 280,312 Q284,292 290,270 C294,220 297,160 298,116 Z")
BANG_R = ("M302,116 C338,128 374,164 382,214 C388,248 388,276 384,300 Q374,302 368,318 Q364,298 358,292 "
          "Q348,304 344,322 Q340,300 334,292 Q326,300 320,312 Q316,292 310,270 C306,220 303,160 302,116 Z")
SIDE_L = "M220,210 C206,260 204,330 212,366 Q200,378 184,384 Q206,390 224,372 C230,330 232,270 230,226 Z"
SIDE_R = "M380,210 C392,244 398,274 392,300 Q386,286 376,282 C378,260 378,236 372,220 Z"
# 毛の流れの線
STRANDS = ["M296,130 C270,170 250,230 244,290", "M292,150 C282,200 272,250 266,292",
           "M286,130 C250,160 232,220 232,300", "M304,130 C330,170 350,230 356,290",
           "M308,150 C318,200 328,250 334,292", "M314,130 C350,160 368,220 368,300"]


def character_svg(expr, uid):
    locks = "".join(f'<path d="{p}"/>' for p in (SIDE_L, SIDE_R, BANG_L, BANG_R))
    strands = "".join(f'<path d="{p}"/>' for p in STRANDS)
    face = ("M221,250 C219,318 234,376 266,408 C282,423 292,431 300,433 C308,431 318,423 334,408 "
            "C366,376 381,318 379,250 C379,196 221,196 221,250 Z")
    face_line = ("M221,250 C219,318 234,376 266,408 C282,423 292,431 300,433 C308,431 318,423 334,408 "
                 "C366,376 381,318 379,250")
    return f'''
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 800" width="600" height="800">
  <defs>
    <linearGradient id="hair" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{HAIR_TOP}"/><stop offset="1" stop-color="{HAIR_BOT}"/>
    </linearGradient>
    <linearGradient id="iris" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#4e2c14"/><stop offset="0.55" stop-color="#9a6030"/>
      <stop offset="1" stop-color="#e2ad6c"/>
    </linearGradient>
    <linearGradient id="jacket" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#e3e5ef"/><stop offset="0.35" stop-color="#fbfbfe"/>
      <stop offset="0.7" stop-color="#f3f4f9"/><stop offset="1" stop-color="#d9dbe7"/>
    </linearGradient>
    <linearGradient id="neck" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{SKIN_SH}"/><stop offset="0.5" stop-color="{SKIN}"/>
    </linearGradient>
    <radialGradient id="blush"><stop offset="0" stop-color="#ff9a9a" stop-opacity="0.55"/>
      <stop offset="1" stop-color="#ff9a9a" stop-opacity="0"/></radialGradient>
    <filter id="soft2"><feGaussianBlur stdDeviation="2"/></filter>
    <filter id="soft6"><feGaussianBlur stdDeviation="6"/></filter>
    <clipPath id="faceclip{uid}"><path d="{face}"/></clipPath>
    <clipPath id="hairclip{uid}">
      <path d="M300,108 C210,108 190,190 196,270 C200,320 206,360 214,380 L386,380 C394,360 402,320 404,270 C410,190 390,108 300,108 Z"/>
    </clipPath>
  </defs>

  <!-- 後ろ髪 -->
  <path d="M300,108 C210,108 190,190 196,270 C200,320 206,360 214,380 L386,380 C394,360 402,320 404,270
           C410,190 390,108 300,108 Z" fill="url(#hair)" stroke="{HAIR_LINE}" stroke-width="1.6"/>

  <!-- 首と体 -->
  <path d="M276,410 L324,410 L328,478 L272,478 Z" fill="url(#neck)"/>
  <path d="M190,540 C230,512 258,500 272,488 L328,488 C342,500 370,512 410,540 L440,800 L160,800 Z" fill="#26262c"/>
  <path d="M272,488 L328,488 L300,560 Z" fill="{SKIN}"/>
  <path d="M272,488 L300,560 L328,488" fill="none" stroke="#1a1a1e" stroke-width="2"/>
  <rect x="270" y="452" width="60" height="14" rx="4" fill="#1e1e22"/>
  <circle cx="300" cy="470" r="5" fill="#c8cad4" stroke="#6a6a74" stroke-width="1.2"/>
  <!-- 白いジャケット -->
  <path d="M262,478 C230,500 170,512 120,548 C96,600 90,700 84,800 L236,800 C240,700 250,600 272,540 Z"
        fill="url(#jacket)" stroke="#9c98a8" stroke-width="1.5"/>
  <path d="M338,478 C370,500 430,512 480,548 C504,600 510,700 516,800 L364,800 C360,700 350,600 328,540 Z"
        fill="url(#jacket)" stroke="#9c98a8" stroke-width="1.5"/>
  <path d="M262,478 L238,506 L256,572 L276,528 Z" fill="#ffffff" stroke="#9c98a8" stroke-width="1.5"/>
  <path d="M338,478 L362,506 L344,572 L324,528 Z" fill="#ffffff" stroke="#9c98a8" stroke-width="1.5"/>
  <path d="M470,640 L512,632 M472,652 L513,644" stroke="#d8483e" stroke-width="4"/>
  <path d="M474,664 L514,656" stroke="#2a2a30" stroke-width="3"/>

  <!-- 耳とピアス -->
  <path d="M222,296 C206,292 204,322 214,340 C220,350 226,350 228,346 Z" fill="{SKIN}" stroke="{LINE}" stroke-width="1.4"/>
  <path d="M378,296 C394,292 396,322 386,340 C380,350 374,350 372,346 Z" fill="{SKIN}" stroke="{LINE}" stroke-width="1.4"/>
  <circle cx="389" cy="330" r="2.6" fill="#d8dae4" stroke="#555" stroke-width="0.8"/>
  <circle cx="387" cy="341" r="3" fill="#2a2a30"/>
  <path d="M383,347 a6,6 0 1 0 8,0" fill="none" stroke="#c8cad4" stroke-width="1.8"/>

  <!-- 顔 -->
  <path d="{face}" fill="{SKIN}"/>
  <path d="{face_line}" fill="none" stroke="{LINE}" stroke-width="1.8"/>
  <g clip-path="url(#faceclip{uid})">
    <g fill="{SKIN_SH}" filter="url(#soft6)" transform="translate(0,9)">
      <path d="{BANG_L}"/><path d="{BANG_R}"/></g>
    <path d="M221,300 C224,360 244,400 268,420 L240,420 Z" fill="{SKIN_SH}" opacity="0.7" filter="url(#soft6)"/>
  </g>
  <ellipse cx="248" cy="374" rx="24" ry="10" fill="url(#blush)"/>
  <ellipse cx="352" cy="374" rx="24" ry="10" fill="url(#blush)"/>
  {eye(258, -1, expr, uid + "L")}
  {eye(342, 1, expr, uid + "R")}
  {brow(258, -1, expr)}
  {brow(342, 1, expr)}
  <path d="M301,366 Q299,373 303,375" fill="none" stroke="#d9a894" stroke-width="1.4" stroke-linecap="round"/>
  {mouth(expr)}

  <!-- 前髪 -->
  <path d="M214,250 C214,150 260,112 300,112 C340,112 386,150 386,250 C360,214 330,200 300,200
           C270,200 240,214 214,250 Z" fill="url(#hair)"/>
  <g fill="url(#hair)" stroke="{HAIR_LINE}" stroke-width="1.5" stroke-linejoin="round">{locks}</g>
  <g fill="none" stroke="{HAIR_LINE}" stroke-width="1.1" opacity="0.45" stroke-linecap="round">{strands}</g>
  <!-- 天使の輪（ツヤ） -->
  <g clip-path="url(#hairclip{uid})">
    <path d="M226,196 C260,166 340,166 374,196" fill="none" stroke="{HAIR_HI}" stroke-width="9" opacity="0.75"
          filter="url(#soft2)"/>
  </g>
  <path d="M300,114 L298,150" stroke="{HAIR_LINE}" stroke-width="1.4" opacity="0.7"/>
</svg>'''


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "kagami_svg_test.png"
    svgs = "".join(character_svg(e, e) for e in ("normal", "serious", "laugh"))
    html = f'<html><body style="margin:0;background:#ecebf4;display:flex">{svgs}</body></html>'
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME)
        pg = b.new_page(viewport={"width": 1800, "height": 800}, device_scale_factor=1)
        pg.set_content(html)
        pg.screenshot(path=out)
        b.close()
    print("wrote", out)


if __name__ == "__main__":
    main()
