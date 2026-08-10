# SongScope v0.2 Phase E1

### D1 build 02 — IndexedDB upgrade待機の修正
- Phase D1でDB version 4→5へ更新する際、旧SongScopeのSafariタブ/PWAがDB接続を保持していると、`indexedDB.open()` が `blocked` のまま無期限待機し、「識別中 / 音声の同一性を確認しています…」で止まって見えるケースがあった。
- `onblocked` を検出してユーザーへ旧画面を閉じる案内を出す。
- DB接続へ `onversionchange` を設定し、今後のschema更新時には旧画面側が接続を自動で閉じるようにした。
- 録音・F0解析・D1 matcher/decisionのアルゴリズムは変更していない。

> **Phase D1 build 01**: 実録音のA/Bでglobal offsetが約4分間一貫し、人間の聴感でも序盤・中盤・終盤の対応を確認できたため、D1を正式化しました。近接offset候補を独立解と誤認しないcandidate clusteringを追加し、候補の質・証拠量・往復整合性・drift・独立候補clusterから `resolved / ambiguous / unresolved` を保守的に判定します。`resolved` のときだけ「この位置合わせを反映」を表示します。

カラオケで録音した自分の歌を、**あとから人間とChatGPTが客観的に比較・検証できるデータ**に変換するための、iPhone向けWebアプリ（PWA）です。

**このアプリは歌の採点をしません。** 上手い・下手の判定もしません。
やることは「測る」「見せる」「書き出す」の3つだけです。判断は人間（とChatGPT）がします。

- 音声はすべて**あなたのiPhoneの中だけ**で処理されます。外部サーバーへの送信は一切ありません。
- ログイン不要・サーバー不要・課金なし。
- Phase A-3までのF0/RMS/スペクトル計算ロジックは変更していません。
- D1は同じ`songId`・別raw音声のA/Bについてchromaからglobal offsetを推定し、`resolved / ambiguous / unresolved` を返します。`resolved` のときだけユーザー操作でoffsetへ反映できます。
- `songId`が誤って分かれた場合は、A/B比較画面の「BをAと同じ曲にまとめる」で明示的に統合できます。
- Schema Version: `0.8.0`
- Build ID: `20260810-e1-01`

## Phase D2 — aligned observation comparison


### D2 build 01 — metric semantics / interpretation guardrails

- D1で揃えた同一区間・同一証拠量のwindowingを正式なD2基盤として採用。
- `metric_catalog.json` を比較ZIPへ追加し、各指標の signal scope / allowed interpretation / prohibited interpretation を機械可読で保存。
- `f0_candidate_hz` は **mixed-audio periodicity candidate** と明記し、true vocal F0 / vocal range / pitch accuracy としての解釈を禁止。
- F0 candidate ratioはvoiced ratio/歌唱時間ではなくestimator evidence。ambiguity=noneも正しさを意味しない。
- `rms_relative_db` は録音内相対値で、絶対音量・歌声の声量差としての解釈を禁止。
- 録音条件のstored metadata一致/不一致/unknownを `recordingConditionComparison` に保存。
- DAM score等の外部結果は `evaluationAnchors` として分離し、音響差の原因とはみなさない。
- DB_VERは5のまま。audio-analysis-worker / alignment-workerは変更しない。

### D2 Diagnostic build 03 — Float32 frame-boundary fix
- build 02で共通alignment区間そのものは正しくなったが、実機出力では6窓でA/BのframeCountが1 frame（0.02秒）ずれるケースが残った。
- 原因は解析frame時刻がメモリ上ではFloat32で保持され、長い録音では境界時刻に数e-5秒程度の丸め誤差が出るのに、build 02の境界toleranceが1e-7秒と小さすぎたこと。
- `[start,end)` の意味は維持したまま、toleranceをframe hopに対して十分小さい0.1 ms以上へ拡大し、同じ共通区間ではA/Bのframe数が安定して一致するよう修正。
- D1 alignment、F0/RMS解析、window幅10秒/hop5秒、IndexedDB schemaは変更していない。

### D2 Diagnostic build 02 — common-overlap windowing fix
- 部分coverage窓でA側を10秒、B側を3.6秒など異なる時間範囲で集計していたため、pairwise comparisonとして不正確だった。build 02では各窓の**共通alignment区間だけ**をA/B両方に使う。
- `pairReferenceStartSec / pairReferenceEndSec` と `comparisonCoverageStatus (full/partial/none)` を出力し、coverage=0の窓では両側の比較観測値をnull/0にする。
- offset後の浮動小数点境界で10秒窓が499/501 frameになりうる問題を微小toleranceで安定化した。
- 現在の10秒/5秒window policyはfull nominal windowsのみ。末尾の未集計時間は`windowingCoverage.unwindowedReferenceTailSec`として明示する。
- D1 alignment、audio-analysis-worker、IndexedDB schemaは変更していない。


- D1のresolved mappingを使い、Recording A基準の10秒窓 / 5秒hopで同一曲位置の観測値を並べる診断段階です。
- 書き出しは `comparison_summary.json` と `comparison_windows.csv` の2ファイルを含むZIPです。
- 初期指標は `rms_relative_db` のp10/p50/p90、`f0_candidate_hz` のp10/p50/p90、F0 candidate量、ambiguity量です。
- ambiguity flagを理由にF0候補を訂正・削除しません。`ambiguity=none`も正しさの保証として扱いません。
- `rms_relative_db` は各録音内で正規化された観測値で、録音間の絶対音量差とは解釈しません。
- D2 Diagnosticは改善/悪化を判定しません。観測・証拠量・ユーザー報告marker/segmentをreference時間へ揃えて保存します。
- IndexedDB schemaはD1 build02と同じDB_VER=5のままです。D2 DiagnosticのためのDB upgradeは行いません。


---

## Phase B-lite identity rules（D1-prepでも維持）

- `recordingId`: raw audio SHA-256が同じなら同じ録音。既存データに同じhashがあればそのIDを再利用します。
- `analysisId`: 解析runごとに新規。最新のfull解析は従来の`analysis`に保持し、全runのcompact provenanceを`analysisHistory`に残します。
- `songId`: 初回採番後は保持する永続グループID。曲名・アーティストの編集だけで変えません。
- `songIdentityKey`: 曲名・アーティストのNFKC正規化値から決定する照合キー。アーティスト未入力時は曲名のみなので、同名異曲の誤グループ化余地を`songIdentityBasis`で明示します。
- `arrangementId`: B-liteでは未確定のまま。キー違い・伴奏違いを同一アレンジと断定しません。
- Phase A-3までのF0/RMS/スペクトル計算ロジックは変更しません。D1-prepでも`audio-analysis-worker.js`は変更しません。


## 目次

1. [ファイルを置く](#1-ファイルを置く)
2. [GitHub Pagesで公開する](#2-github-pagesで公開するhttps環境が必要です)
3. [iPhone Safariで開く](#3-iphone-safariで開く)
4. [ホーム画面に追加する](#4-ホーム画面に追加する)
5. [ボイスメモから録音を書き出す](#5-ボイスメモから録音を書き出す)
6. [SongScopeへ読み込む](#6-songscopeへ読み込む)
7. [レビューする](#7-レビューする)
8. [分析データを書き出す](#8-chatgpt用分析データを書き出す)
9. [ZIPをChatGPTへ渡す](#9-生成されたzipをchatgptへ渡す)
10. [データの保存とバックアップ](#10-データの保存とバックアップ大事)
11. [数値の読み方と注意](#11-数値の読み方とても大事)
12. [ファイル構成](#12-ファイル構成)
13. [困ったときは](#13-困ったときは)

---

## 1. ファイルを置く

PCで、以下のファイルを**同じフォルダ**にまとめます（フォルダ名は何でも構いません）。

```
songscope/
├─ index.html
├─ styles.css
├─ app.js
├─ audio-analysis-worker.js
├─ alignment-worker.js
├─ manifest.json
├─ service-worker.js
├─ README.md
├─ zip.js
├─ icon-180.png
├─ icon-192.png
└─ icon-512.png
```

**注意：** 現在のGitHub Pages版はすべてルート直下に置く構成です。ファイル名は変えないでください。`app.js` は `audio-analysis-worker.js` を、`index.html` は `zip.js` と `app.js` をこの名前で読み込みます。

> PCのブラウザで `index.html` をダブルクリックして開くだけでも動作しますが、**Web Worker と Service Worker が動かないため**、解析が始まらないことがあります。次の手順でHTTPS環境に置くのが確実です。

---

## 2. GitHub Pagesで公開する（HTTPS環境が必要です）

iPhoneのSafariでPWAとして使うには、`https://` で始まるアドレスが必要です。無料のGitHub Pagesが手軽です。

1. <https://github.com> でアカウントを作り、ログインします。
2. 右上の「+」→ **New repository** をクリック。
3. Repository name に `songscope` と入力。**Public** を選び、**Create repository**。
4. 作られたページの「**uploading an existing file**」をクリック。
5. さきほどのフォルダの中身（`index.html` など）を**まとめてドラッグ＆ドロップ**します。
   - `lib` フォルダと `icons` フォルダも忘れずに。フォルダごとドラッグすれば構造が保たれます。
6. 下の **Commit changes** を押します。
7. リポジトリの **Settings**（歯車）→ 左メニューの **Pages** を開きます。
8. Source を **Deploy from a branch**、Branch を **main** / **/(root)** にして **Save**。
9. 1〜2分待つと、上部に公開URLが表示されます。

```
https://<あなたのユーザー名>.github.io/songscope/
```

このURLをメモしておきます（自分にメールしておくと楽です）。

> **公開範囲について**：GitHub Pagesは誰でもアクセスできるURLになりますが、公開されるのは**アプリのプログラムだけ**です。あなたの録音・マーカー・解析結果はiPhoneの中にしか保存されず、アップロードされません。

---

## 3. iPhone Safariで開く

iPhoneの **Safari**（Chromeではなく）で、上のURLを開きます。
「SongScope」のホーム画面が出れば成功です。

---

## 4. ホーム画面に追加する

アプリのように使えるようになります（アドレスバーが消え、画面が広くなります）。

1. Safariの下の **共有ボタン**（□に↑）をタップ。
2. 下へスクロールして「**ホーム画面に追加**」をタップ。
3. 名前を確認して「**追加**」。

以降はホーム画面のアイコンから起動できます。

> **重要**：Safariで開いたときと、ホーム画面のアイコンから開いたときで、**保存データが別扱いになる場合があります**。どちらか片方に決めて使うことをおすすめします（ホーム画面版がおすすめ）。

---

## 5. ボイスメモから録音を書き出す

カラオケでの録音は、iPhone標準の「**ボイスメモ**」アプリで行います。

**録音のコツ（比較しやすくするため）**

- 毎回できるだけ**同じ置き方**にする（例：テーブルの上・画面を上向き・自分から約50cm）。
- 置き場所を変えた日は、アプリの「詳細を追加」→「録音条件プリセット」にメモしておく。

**書き出し手順**

1. ボイスメモアプリで対象の録音をタップ。
2. 「**…**」（その他）→「**共有**」をタップ。
3. 「**"ファイル"に保存**」を選び、保存先（例：iCloud Drive や このiPhone内）を決めて保存。

これで `.m4a` ファイルがFilesアプリに入ります。

---

## 6. SongScopeへ読み込む

1. SongScopeのホームで「**＋ 録音を追加**」をタップ。
2. ファイル選択画面が開くので、「**ファイルを選択**」→ さきほど保存した `.m4a` を選びます。
3. **曲名**を入力します（必須はこれだけです）。
   - DAM点数・キー・機種などは「**詳細を追加**」を開いたときだけ入力すればOK。毎回入力する必要はありません。
4. 「**保存**」を押すと、レビュー画面へ移動し、**自動で解析が始まります**（「解析中 35%」のように表示）。

対応形式：`m4a`（ボイスメモの標準） / `mp3` / `wav`
解析は4〜6分の録音で数十秒程度かかります。解析中も再生やマーカー登録は使えます。

> 「この音声形式はこのブラウザでは解析できません」と出た場合、そのファイルはSafariがデコードできない形式です。**それでも再生と手動レビューは使えます**。

---

## 7. レビューする

やることは基本この2つだけです。

**(A) 気になったところでボタンを押す**

再生しながら、画面下の「**ここにマーカー**」を押すと、**その瞬間の時刻が自動で記録されます**。
続いてタグを選びます（高音／リズム／力み／語尾／良かった…など）。

> 原因が自分でも分からないときは、無理に分類せず「**違和感**」を選んでください。あとから見返すためのタグです。

**(B) 気になる区間を繰り返し聴く（A-Bループ）**

1. 気になる箇所の手前で「**A地点**」を押す。
2. 終わりで「**B地点**」を押す。
3. 「**ループ開始**」でその区間を繰り返し再生。
4. 「**区間として保存**」を押すと、タグ・メモ付きで保存され、**その区間の統計値（音量・F0など）が自動計算**されます。

「A −0.1 / +0.1」ボタンで0.1秒単位の微調整ができます。

**画面の見方**

上から順に、波形／音量エンベロープ／推定F0／スペクトログラム。**横軸はすべて同じ時間軸**で、あなたが付けたマーカーと区間が全部のグラフに重なって表示されます。グラフをタップするとその時刻へジャンプします。

- **推定F0**：色が濃いほど信頼度（confidence）が高い点です。スライダーで表示する下限を変えられます。「MIDI表示」で音名相当の目盛りに切り替わります。
- **スペクトログラム**：明るいほど強い成分です。「0–4kHz」ボタンで表示範囲を切り替えられます。

マーカー・区間・メモ・録音情報は**すべて自動保存**です。保存ボタンはありません。

---

## 8. 「ChatGPT用分析データを書き出す」

レビュー画面をいちばん下までスクロールして、青いボタンを1回押すだけです。

ZIPファイル（`songscope_曲名_日時.zip`）が作られ、iPhoneの共有シートが開きます。
「**"ファイル"に保存**」を選べばFilesアプリに保存されます。

**ZIPの中身**

| ファイル | 内容 |
|---|---|
| `report.md` | ChatGPTにそのまま読ませる用のまとめ（人が読んでも分かります） |
| `summary.json` | 機械処理用。解析設定・アルゴリズム名とバージョンも入っています |
| `frames.csv` | 20msごとの全特徴量（音量・F0・スペクトル） |
| `markers.csv` | あなたが押したマーカー |
| `user_segments.csv` | あなたが指定した区間＋その統計値 |
| `detected_segments.csv` | 解析エンジンが自動検出した活動区間 |
| `waveform.png` `loudness.png` `pitch.png` `spectrogram.png` | グラフ画像（横1600px。マーカーも描き込まれています） |

「**元音声もZIPへ含める**」をONにすると音声ファイルも入りますが、サイズが大きくなるため**既定はOFF**です。

---

## 9. 生成されたZIPをChatGPTへ渡す

ChatGPTはZIPのままアップロードできます（できない場合はFilesアプリでZIPを展開して、中身をまとめてアップロードしてください）。

**プロンプト例**

```
添付は歌唱録音の観測データです。SongScopeというツールで書き出しました。

前提:
- これはカラオケ伴奏を含む録音です。ピッチ・スペクトル系の値には伴奏が混入しています。
- 絶対値での「上手い/下手」判定はしないでください。
- report.md の Recording limitations を必ず踏まえてください。

お願い:
1. まず「観測された事実」だけを箇条書きにしてください。
2. 私が付けたマーカー・区間（主観）と、同じ時刻の測定値（客観）の対応を整理してください。
3. そこから立てられる「仮説」を、断定せずに複数挙げてください。
4. 次回の録音で仮説を検証するための、具体的な実験手順を提案してください。
```

同じ曲の別テイクを比較したいときは、ZIPを2つ渡して「AとBを比較してください。ただし録音条件が異なる可能性があるため、絶対音量の比較は避けてください」と伝えます。

アプリ内にも簡易的な **A/B比較** 画面があります（ホーム右上の「A/B比較」）。2つの録音の音量エンベロープを重ね、Bの開始位置を手動でずらして揃えられます。

---

## 10. データの保存とバックアップ（大事）

**iOSでは、ブラウザの保存領域がOSの判断で削除されることがあります。**
このアプリの中のデータは「消えない保証がない」と考えてください。

対策：

1. **原本をボイスメモ側に残しておく。** 解析結果は原本があればいつでも作り直せます。
2. ホーム画面の「**永続化を要求**」を押しておく（端末が対応していれば削除されにくくなります）。
3. ときどき「**全データをJSONで書き出す**」でバックアップする。
   - このJSONには録音メタ情報・マーカー・区間・解析サマリーが入ります（音声とフレーム単位データは含みません。これらは原本から再解析できます）。
4. 大事な録音は、そのつどZIPを書き出して保管する。

---

## 11. 数値の読み方（とても大事）

このアプリが出す数値には、**構造的な限界**があります。隠さずに書きます。

**伴奏が混ざります**
録音には、あなたの声・カラオケ伴奏・部屋の反響・周囲の音が全部入っています。
そのため **推定F0・有声確率・スペクトル系の値は「あなたの声だけ」を表していません**。
特にF0は、伴奏のベースや和音の影響で、実際の歌よりオクターブ下の値を返すことがあります。confidenceの低い点や、明らかに歌っていない区間の値は、疑ってください。

**絶対dBで比較しないでください**
iPhoneのマイク特性・自動ゲイン・録音距離・部屋で、音量の絶対値は簡単に変わります。
「RMSが−18 dBだから声量が足りない」といった判断はできません。
使い方は **同じ曲の中での強弱の変化**と、**似た条件で録った録音同士の比較**です。

**「検出区間」は「発声区間」ではありません**
`detectedActiveSegment` は、その録音の中で相対的に音量が高い区間です。伴奏だけの部分も含まれます。

**実装していないもの（v0.1）**
jitter / shimmer / HNR / CPP / フォルマント / MFCC は実装していません。
伴奏込みの録音ではこれらの値は本人の声帯振動を表さず、**「精密そうに見える間違った数値」**になるためです。値が欲しくなったら、伴奏なしのアカペラ録音を別途用意するのが正しい順序です。

同じ理由で、原曲メロディとの音程比較・歌詞の自動取得・歌唱力の点数化は、意図的に実装していません。

**解析方法のバージョンは記録されます**
`summary.json` には `analysisEngineVersion` / `algorithmNames` / `algorithmVersions` / `analysisSettings` が入ります。半年後に解析方法を変えても、過去の結果がどの方法で作られたか分かります。解析設定（フレーム長・F0範囲・信頼度下限など）はホーム右上の「設定」から変更でき、**次回の解析から反映**されます。

---

## 12. ファイル構成

| ファイル | 役割 |
|---|---|
| `index.html` | 画面の構造（ホーム／レビュー／比較／各種シート） |
| `styles.css` | 見た目。ダークモードは自動で切り替わります |
| `app.js` | UI・保存(IndexedDB)・グラフ描画・書き出し |
| `audio-analysis-worker.js` | 音響解析の本体。別スレッドで動くので画面が固まりません |
| `alignment-worker.js` | D1用。chroma特徴抽出、global offset探索、candidate clustering、保守的なresolved判定。歌唱観測workerとは分離 |
| `zip.js` | ZIP生成（無圧縮）。自作・ローカル同梱・通信なし |
| `manifest.json` | ホーム画面に追加したときの名前やアイコン |
| `service-worker.js` | オフライン起動用のキャッシュ（アプリ本体のみ。録音は扱いません） |

**外部CDNへの依存はゼロです。** FFT・YIN（ピッチ推定）・ZIP生成はすべて自前実装で、音声データがネットワークへ出る経路はありません。

**保存先の使い分け**
- IndexedDB：音声Blob・解析結果・マーカー・区間
- localStorage：解析設定など軽量な値のみ（音声は保存しません）

---

## 13. 困ったときは

**解析が始まらない / 0%のまま**
`file://` で直接開いていませんか。HTTPS（GitHub Pagesなど）で開いてください。

**「この音声形式はこのブラウザでは解析できません」**
Safariがデコードできない形式です。ボイスメモから書き出した `.m4a` をお使いください。この場合も再生・マーカー・区間・report.md の書き出しは使えます。

**解析が遅い / 途中で止まる**
10分を超える録音は端末のメモリを圧迫します。まずは4〜6分で試してください。設定で `frameSizeMs` を大きく、`hopSizeMs` を大きくすると軽くなります（時間分解能は下がります）。

**書き出したZIPが見つからない**
共有シートで「"ファイル"に保存」を選ぶと、Filesアプリの選んだ場所に入ります。

**アプリを更新したのに古いまま**
Service Workerがキャッシュしています。ホーム画面のアイコンを一度削除し、Safariで開き直してから追加し直してください。

**保存したデータが消えた**
iOSがストレージを解放した可能性があります。原本の音声から読み込み直せば、解析はやり直せます（10章を参照）。

---

## このアプリの使い方の全体像

```
録音（ボイスメモ）
   ↓
観測（SongScopeが測る：波形・音量・F0・スペクトル）
   ↓
主観の記録（あなたがマーカーと区間を押す）
   ↓
書き出し（ZIP）
   ↓
仮説（人間とChatGPTが考える）
   ↓
実験（次のカラオケで条件を変えて録る）
   ↓
検証（同じ形式のデータ同士で比べる）
   ↓ ↑
   繰り返す
```

判断するのはあなたです。このアプリは、そのための目盛りを用意するだけです。

---

SongScope v0.1.0 — 端末内処理 / 採点なし / 観測データのみ


### A-2 Diagnostic build 02
- 画面のバージョン表示に buildId を併記。
- mutable app assets の network-first fetch ではブラウザ HTTP cache を使わない。
- F0 アルゴリズム本体は A-1 から変更していない。


### A-3: F0 candidate / ambiguity

- `f0_candidate_hz` は、YINのraw候補のうち confidence >= 0.70 を満たした観測候補です。既存の `voiced_probability` は本人歌声の確率ではなく、F0 confidence と録音内レベルゲートを掛けた複合指標なので、A-3では候補採用の必須条件から外し、補助的な証拠量としてだけ残します。
- 旧 `usable_vocal_f0_hz` は後方互換のため残しますが、本人声の確定F0とは解釈しません。A-3では孤立点を勝手に削除せず candidate として保持し、必要なら `legacy_isolated_disagreement` を付けます。
- `f0_ambiguity_level` は `none / caution / strong`。`f0_ambiguity_flags` は局所2x/3x/4x関係、急速な切替、旧isolated判定との不一致を記録します。
- 判定窓は local ±0.12 s、rapid ±0.04 s、整数比許容幅 ±50 cent。これは『誤り検出』ではなく、混合カラオケ音声で絶対F0を比較するときの注意フラグです。
- `summary.json` に candidate の証拠量、p05/p50/p95、曖昧性件数と使用閾値を保存します。最大値・最小値を声域とは呼びません。
- F0アルゴリズムそのものは `1.1.0-phaseA1` のままです。A-3で追加したのは `f0Ambiguity: 1.0.0-phaseA3` だけです。


### B-lite build 02 identity rule

- `songId` is persistent once assigned; editing title/artist does not silently change it.
- `songIdentityKey` is the NFKC-normalized title/artist matching key and may change when metadata is corrected.
- A new recording with the same `songIdentityKey` reuses the existing `songId` when available.

### build 02 fix
- 同一音源の再解析直後でも、画面・ZIPが最新の `latestAnalysisId` と `analysisCount` を参照するよう、解析完了時に `state.rec` を永続化済みrecordingへ同期します。
- 音響解析アルゴリズム、identity判定、時間座標定義は変更していません。


### D1 Diagnostic build 01
- `alignment-worker.js` を新設。`audio-analysis-worker.js` は変更しません。
- Aをreference、Bをtargetとし、時間規約は `A time = B time + offsetSec` です。
- 混合カラオケ音声から STFT pitch-class chroma（log圧縮、L2正規化、時間平滑化）を作り、12通りのchroma回転とglobal offsetをcoarse→refineで探索します。
- 出力は上位5候補、overlap/coverage、block similarity、逆向き検査、early/middle/late drift probe。similarityは確率ではありません。
- 診断結果は自動でoffsetへ適用しません。比較画面の数値入力で人間が候補を手動確認できます。
- `alignmentFeatures` は `audioSha256 + featureAlgorithmVersion` でIndexedDBにキャッシュします。
- `alignmentDiagnostics` は診断履歴として保存し、単独JSONで書き出せます。これは正式alignmentではありません。

### D1 build 01 formalization
- matching versionを `global-offset-coarse-refine-v2` に更新。chroma特徴量は `stft-chroma-log-l2-smooth-v1` のままです。
- 近接したoffset候補は同じ局所解の肩としてcluster化し、離れた独立clusterだけを競合候補として扱います。
- `resolved / ambiguous / unresolved` は、mean similarity、block P10、短い方のcoverage、A→B/B→Aのoffset/rotation整合性、early/middle/late drift、独立cluster間marginを別々のcheckとして保存してから判定します。similarityは確率に変換しません。
- `resolved` のときだけ「この位置合わせを反映」を表示します。自動で勝手にoffsetを書き換えません。
- `alignmentResults` にはpairごとの最新D1判定（resolved / ambiguous / unresolved）を保存し、resolved時だけcanonical mappingを持たせます。将来D2はresolved mappingだけを参照します。`alignmentDiagnostics` は各判定runの根拠として残します。
- `audio-analysis-worker.js` は変更していません。


### Phase E1 build 01 — Outcome / Evaluation evidence
- D2の観測比較は変更せず、外部評価を別レイヤーの evidence として保存します。
- レビュー画面から採点結果画像を1枚添付できます。画像は元音声と同じ IndexedDB の recording asset に紐づけ、SongScope自身はOCR・採点項目解釈を行いません。
- 通常ZIPへ `evaluation_anchors.json` と、添付時は `evaluation/scoring_result_image.*` を追加します。D2比較ZIPにも `evaluation_anchors.json` と A/B の添付画像を含めます。
- DAM点数・recordedAtなどに metadata provenance を追加します。既存データで由来を証明できない値は `legacy_unknown` のままにし、推測で user-confirmed にしません。
- 新規録音の recordedAt がファイルの lastModified 由来なら `file_last_modified_unverified`、日時をユーザーが編集した場合は `user_edited / user_confirmed` と記録します。
- DB_VERは5のままです。新しいObjectStoreは作らず、D1のDB upgrade問題を再発させません。


## Phase E2 build 01 — 外部構造化評価の安全な取込

- SongScope自身は採点結果画像をOCRしません。代わりに、ChatGPT等の外部解釈で作成した `songscope-external-evaluation-v1` JSONを読み込めます。
- 取込時に `recordingId` と、添付済み採点結果画像の SHA-256 を必須照合します。違う録音・違う画像の評価JSONは拒否します。
- 構造化評価は元画像・手入力DAM点数とは別の証拠として保持し、値が食い違っても自動補正・上書きしません。
- 通常ZIPには `evaluation/structured_scoring_result.json`、D2比較ZIPには A/B各側の構造化評価JSONを含めます。
- D2の `evaluationAnchors.structuredScoringResults` は、画像SHA照合済みの総合点が両側にある場合のみ差分を出します。採点条件の比較可能性は別判定のままです。
- DB schemaは変更せず `DB_VER=5` のまま。構造化評価は既存audio assetの追加プロパティとして保存します。
- 採点結果画像を含むZIPには `evaluation/extraction_request.json`（比較ZIPではA/B別）も同梱し、外部解釈側へ録音ID・画像SHA・出力schema・禁止推測を機械可読で伝えます。
