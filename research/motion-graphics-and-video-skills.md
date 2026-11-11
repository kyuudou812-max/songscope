# モーショングラフィックスと動画制作に必要なスキル：勉強ノート

調査日: 2026-10-08
[出典] … ネットの資料で確認したこと / [一般知識] … 私の既存知識で、今回は資料まで確認していないこと

---

## 0. 動画制作のスキルの全体像

| 段階 | スキル | このプロジェクトでの担当 |
|---|---|---|
| 企画 | 主題を1つに絞る、絵コンテ、秒割り、仮の動画（アニマティック）で確かめる | 済（STORYBOARD.md、プレビュー） |
| 素材 | 背景・文字・効果の素材づくり | 背景はユーザー、他は Claude |
| **動き** | イージング、タイミング、予備動作・余韻、ずらし | 本ノート 1章 |
| **文字** | 動く文字の読みやすさ、階層、表示時間 | 2章 |
| **タイトル** | 象徴を1つ選ぶ、質感、音との同期 | 3章 |
| **編集** | カットの判断基準、つなぎ方の種類、リズム | 4章 |
| **音** | 無音、唸り、上昇音、一撃、音と映像のずれの許容範囲 | 5章 |
| **色** | 黒のつぶし方、色かぶり、彩度 | 6章 |
| ホラー特有 | 静止、空白、気配 | 7章 |
| 書き出し | 形式・容量・光の点滅への配慮 | 8章 |

---

## 1. 動きの原則（モーショングラフィックスの基本）

アニメーションの12原則のうち、モーショングラフィックスで特に効くのは **イージング・タイミング・予備動作・余韻（フォロースルー）** の4つ。[出典: Made Good Designs, Figma]

### イージング（加速と減速）
- 現実の物は一定の速さでは動かない。等速（リニア）は「選ばなかった結果」になりがち。[出典]
- **入ってくるものは ease-out（速く来て、ゆっくり止まる）、出ていくものは ease-in（ゆっくり動き出して、速く去る）、画面内の移動は ease-in-out。** [出典]
- あえて等速にすると、機械的・記号的な質感になる（例：タイプライターの文字送り）。[出典]

### タイミング（何コマかけるか）
- コマ数が多いと重く力強く、少ないと軽く素早く見える。同じ動きでも性格が変わる。[出典]
- 落ち着いた作品はゆっくり、勢いのある作品は速く。[出典]

### 予備動作と余韻
- 予備動作：本番の動きの前に、2〜4コマだけ逆方向へ動く（ジャンプ前にしゃがむ）。ないと唐突に見える。[出典]
- 余韻・重なり：主の動きが止まったあとも、影や付属物が少し遅れて動く。**ずらし（stagger）** で作る。[出典]
- 行き過ぎて戻る（オーバーシュート）は、遊びのある表現向き。使いすぎると軽く安っぽくなる。[出典]

### 心がまえ
- **「なぜこれは動くのか」を決めてから動かす。** [出典: Made Good Designs]
- 「モーションをデザインすることは、時間をデザインすること」。[出典: Figma]
- 複雑な動きも、単純な動き（直線・円の広がり）の重ね合わせ。[出典]

## 2. 動く文字（キネティック・タイポグラフィ）

- 動く文字は、止まった文字より読みにくい。**コントラストを高く、書体ファミリーは1つ、太さで階層を作る。** [出典]
- 大事な言葉は **3秒くらい** 画面に残すのが目安。1画面に3〜7語。[出典]
- 動きの速さで階層を作る：つかみは速く、主張は止めて見せ、最後は一番長く残す。[出典]
- 日本語を読む速さは、1秒に7〜10文字くらいが目安。[一般知識]
  - **このOPの辞書カードは約50文字あるので、読み切るには5〜7秒必要。** 今は打ち出し約3秒＋残り約1秒なので、読み終わる前に終わる可能性が高い。

## 3. タイトルデザイン

### ソール・バス（タイトルデザインの父）
- **作品を象徴する図形を1つだけ選び、そこにすべてを託す。**（『めまい』の渦巻き、『黄金の腕』のぎざぎざの腕）[出典: Criterion, DesignCrowd]
- 不要な要素はすべて削る。線・形・動きのひとつひとつに目的がある。[出典]
- 動きと文字を音楽に合わせる。タイトルを「名前の一覧」ではなく作品の一部にする。[出典]

### カイル・クーパー『セブン』（1995）
- ほとんどをコンピューターではなく**手作業**で作った。文字はフィルムを引っかき、こすり、揺らし、ピントを外し、光を漏らして歪めた。[出典: The Fincher Analyst]
- 文字が手書きやタイプライターのように見え、ぼやけ、跳ねる。**質感そのものが不安をつくる。** [出典: Screening the Past]
- 犯人のノートや道具の接写を差し込み、「人物の頭の中」を見せる。[出典]

## 4. 編集

### ウォルター・マーチの「6つのルール」（『映画の瞬き』）
カットの良し悪しを、重要な順に判断する。

| 順位 | 基準 | 重み |
|---|---|---|
| 1 | **感情** | 51% |
| 2 | 物語 | 23% |
| 3 | リズム（一呼吸、まばたき、沈黙の長さ） | 10% |
| 4 | 視線の流れ | 7% |
| 5 | 画面上の平面的な位置 | 5% |
| 6 | 空間のつながり | 4% |

**全部を満たせないときは、下から捨てる。感情は最後まで守る。** [出典: StudioBinder, No Film School]

### つなぎ方の種類 [出典: No Film School, Vimeo, Soundstripe]
| 名前 | 中身 | ホラーでの使い方 |
|---|---|---|
| マッチカット | 形や動きが似た2つの画面をつなぐ（『2001年宇宙の旅』の骨→宇宙船） | 形の連想で不気味さをつなぐ |
| スマッシュカット | うるさい→静か（またはその逆）へ突然切り替える | 静寂からの一撃、一撃からの静寂 |
| Jカット | **次の場面の音が、映像より先に始まる** | 何かが来る気配を先に聞かせる |
| Lカット | 前の場面の音が、次の映像に残る | 余韻・不安を引きずる |
| ハードカット | 流れを無視して切って驚かせる | 驚かせる瞬間 |

## 5. 音（ホラーの音づくり）

- **予告編の定番の流れ**：静かな画面 → 上昇音（または逆再生の盛り上がり）→ 黒へのカット → 一撃（スティンガー）→ 突然の静寂。[出典: ホラー予告編の解説]
- 逆再生の盛り上がり音は、一撃に向かって「吸い込まれる」ので、見る人が一拍早く身構える。タイトルや黒へのカットに使う。[出典]
- 一撃にも種類がある。胸に響く鈍い衝撃は「重さ」、鋭い高音は「驚き」。[出典]
- **不協和音**：解決しない響きが不安を生む。[出典]
- **シェパードトーン**：終わりなく上がり（下がり）続けるように聞こえる錯覚。じわじわ迫る不安に使える。[出典: Popular Science]
- **超低音**：聞こえにくい低い音を体で感じさせる。ただし効果の研究は少ない。[出典]
- **静寂**：「ホラーを無音で見ると怖くない」＝音が想像の隙間を埋めている。[出典: LBB]
- 日本のホラー（『リング』『呪怨』）の音楽は、**音色の変化と大量の無音** に頼っていて、歌舞伎の幽霊の場面の伝統につながる。[出典: Wierzbicki]
- 音と映像のずれの許容範囲：音が映像より**約45ミリ秒早い**か、**約125ミリ秒遅い**と気づかれ始める（ITU-R BT.1359）。[一般知識]
  - ココフォリアの技術検証で「音のずれ」を測ったら、この範囲と比べて判断する。

## 6. 色

- 黒をつぶす（暗部を真っ黒に寄せる）と「見えない空間」ができる。ただし大事な部分まで潰さない。暗い画面やスマホでも確認する。[出典: 各種フォーラム]
- **完全な白黒にせず、色を少し残す**ほうが「何かがおかしい」と感じさせる。[出典]
- 緑・青緑の色かぶりは病気・腐敗・超自然と結びつく。冷たい青灰色も定番。[出典]
- このシナリオの表紙は赤茶色なので、**赤茶をうっすら残し、彩度を落とす**のが合う。[一般知識]

## 7. 日本のホラーの見せ方

- 建物や空間の**空っぽさ・孤立**そのものを意味として扱う。[出典: Balmain]
- 見る側に「状況を見下ろす安全な立場」を与えない。[出典]
- 静止した、あいまいな画面が、見る人の支配感を奪って不安にさせる。[出典]
- このシナリオの「何もいない暗闇に、形を見出してしまう」という主題と、そのまま重なる。

## 8. 書き出しと配慮

- **光の点滅は、1秒に3回まで**（WCAG 2.3.1）。特に赤い点滅は危険が大きい。[出典: W3C]
  - 蛍光灯の明滅や反転を使うときは、この基準を超えない。
- 容量：画面全体に細かいノイズを入れると急に重くなる（実測済み、TECHNIQUES.md）。

---

## このOPに当てはめると（改善案）

| # | 学んだこと | 今のOP | 改善案 |
|---|---|---|---|
| 1 | ソール・バス：象徴を1つに | ドアと暗闇 | **ドアの隙間（縦の黒い線）を唯一の象徴にする** |
| 2 | マッチカット | 8秒で黒に切り替わり、タイトルは別の位置に出る | **隙間の縦線と同じ位置・形で、縦書きタイトルが現れる**（形でつなぐ） |
| 3 | 予告編の音の流れ | 8秒で唸りが突然消える | 消える直前に**逆再生の盛り上がり音（約1秒）**を入れ、黒へのカットに吸い込ませる |
| 4 | Jカット | タイトルと一撃が同時 | 一撃を数コマ先に鳴らし、映像が遅れて追いつく |
| 5 | 文字の表示時間 | 辞書カード約4秒 | 打ち出しを速くするか、最後の止めを長くして、**合計6秒前後**確保する |
| 6 | イージング | 一文は ease-in-out で浮かぶ | 入ってくる動きは ease-out にそろえる |
| 7 | セブンの質感 | 文字はきれいなまま | タイトルにだけ、**にじみ・かすかな揺れ**（手作業のような不完全さ）を足す |
| 8 | 日本のホラー：静止と空白 | ドアは動かない | そのまま維持（正しい方向） |
| 9 | 点滅の配慮 | 点滅なし | 明滅を足すなら1秒3回まで |

---

## 出典
- [Made Good Designs: Motion Design Principles Explained](https://madegooddesigns.com/motion-design-principles/)
- [Figma: Principles in motion](https://www.figma.com/blog/principles-in-motion/) / [日本語版](https://www.figma.com/ja-jp/blog/principles-in-motion/)
- [Graduate School USA: Animation Principles Every Motion Designer Should Know](https://www.graduateschool.edu/learn/premiere-pro/animation-principles-motion)
- [Kinetic Typography Quickstart（HackerNoon）](https://sia.hackernoon.com/kinetic-typography-quickstart-guide-for-devs-designers-d5c6b5545ade)
- [Dolić et al., GRID 2024（動く文字の読みやすさの研究）](https://www.grid.uns.ac.rs/symposium/download/2024/89.pdf)
- [Criterion: Credit Where It's Due — The Father of the Title Sequence](https://www.criterion.com/current/posts/6937-credit-where-it-s-due-the-father-of-the-title-sequence)
- [DesignCrowd: Saul Bass](https://blog.designcrowd.com.au/article/2175/graphic-designer-spotlight-saul-bass)
- [The Fincher Analyst: Murder by Imitation — Se7en's Title Sequence](https://thefincheranalyst.com/2018/04/08/murder-by-imitation-the-influence-of-se7ens-title-sequence/)
- [Screening the Past: Se7en's Title Sequence](https://www.screeningthepast.com/?p=14877)
- [StudioBinder: Walter Murch Rule of Six](https://studiobinder.com/blog/walter-murch-rule-of-six)
- [No Film School: Murch's 6 rules](https://nofilmschool.com/2016/11/6-rules-good-cutting-according-oscar-winning-editor-walter-murch)
- [No Film School: Eight Essential Cuts](https://nofilmschool.com/essential-cuts-every-video-editor-needs-know)
- [Vimeo: Jump cuts, L-cuts, and J-cuts](https://vimeo.com/blog/post/guide-to-film-cuts)
- [Soundstripe: J cuts and L cuts](https://www.soundstripe.com/blogs/a-video-editors-guide-to-j-cuts-and-l-cuts)
- [Morphic: Horror stinger sound effects](https://morphic.com/resources/sounds/horror-stinger-sound-effects)
- [LBB: Horror sound design secrets](https://lbbonline.com/news/horror-sound-designs-secrets-how-audio-experts-craft-bone-chilling-scares/)
- [Popular Science: Shepard tone](https://www.popsci.com/science/shepard-tone/)
- [ELVTR: How sound designers manipulate psychology in horror](https://elvtr.com/blog/how-sound-designers-manipulate-human-psychology-in-horror-and-thrillers)
- [Balmain: J-horror（Electronic Journal of Contemporary Japanese Studies）](https://japanesestudies.org.uk/discussionpapers/2006/Balmain.html)
- [Wierzbicki: J-horror soundtracks（Equinox）](https://www.equinoxpub.com/journals/index.php/books/rt/metadata/19136)
- [FreeVisuals: Horror & Thriller Desaturated LUT](https://www.freevisuals.net/luts/free-horror-thriller-desaturated-lut)
- [W3C: Understanding SC 2.3.1 Three Flashes or Below Threshold](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html)
