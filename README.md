# G0 build06 — standalone structured scoring result

- `scoringEvidenceSets` に外部AIの構造化採点JSONを戻して保存できるようにした。
- 新schema: `songscope-external-scoring-result-v1`。未紐付け段階では `recordingId` を受け付けない。
- source verification は `evidenceSetId` と全画像SHA-256集合の完全一致で判定する。
- `source_verified` と人間の内容確認 `userReview.status = user_confirmed` は別管理。JSON差し替え時は user review を必ず未確認へ戻す。
- 抽出ZIPは構造化結果が存在すれば `structured_scoring_result.json` と verification/user review sidecar を含める。
- 録音へのbindingはこのbuildでは実装しない。


## Audit Remediation R2 build 01 — 観測方向の意味論修正 / mixed-audio隔離

- App: `0.2.0-g0` / Build: `20260811-g0-01` / schema: `0.16.0` / DB: `6`
- F2の「pattern / signal / trend」という表現を廃止し、`same_song_observed_take_direction_history`として記述的な履歴圧縮に変更。
- 3件/5件は統計的な格付けではなく、単なる観測テイク数（evidence volume）としてのみ保持。
- 全step同値 (`same`) はdirectional summaryへ昇格しない。`descriptive_only` と `non_monotonic` も除外。
- `physicalRecordingCount` は「実世界で歌った全回数」ではなく「SongScopeに観測/取込されたphysical recording数」と明示。
- mixed-audio F0 / F0 candidate ratio / ambiguity / RMS は `practiceLayerEligible: false`。D2診断ZIPには残すが、Practice/Hypothesisの歌手固有証拠として使わない。
- R2 packageは `practiceLayerPolicy` を持ち、外部AIが使ってよい証拠scopeとdiagnostic-only scopeを機械可読に分離。
- 音響worker、D1 alignment、DB schemaは変更なし。

# SongScope v0.2 Audit Remediation R1 build 01

R0で完全バックアップ/災害復旧を実機検証した後の、**chronology と採点条件の整合性・入力負荷**を直す監査対応。音響workerとD1 matcher自体は変更しない。

- App: `0.2.0-auditR1` / Build: `20260810-r1-01` / schema: `0.14.0` / DB: `6`
- `pairContexts` storeを新設。A/Bの本人確認（時間順・採点4条件）をD1 `alignmentResults` から分離し、**sorted raw audio SHA-256 pairだけ**で永続化する。alignment algorithm/versionを変更しても本人確認は失われない。
- DB5の既存 `alignmentResults.comparisonContext` は起動時に非破壊で `pairContexts` へ移行する。旧alignment resultは監査証拠として残す。
- R0(DB5)の `songscope-full-backup-v1` はR1でも復旧可能。旧ZIPに存在しない `pairContexts` は空storeとして扱い、復旧後の通常起動でlegacy contextを移行できる。
- 録音日時は「この録音日時で合っている」を1タップで `user_confirmed` にできる。**user-confirmed recordedAtをchronologyの主経路**にし、A/Bの「Aが先/Bが先」はfallbackとする。両者が矛盾した場合は自動解決しない。
- AIが採点画像から抽出した `scoringDate` は、画像SHAがsource-verifiedでも `userReview=user_confirmed` になるまではhard chronology evidenceに使わない。
- 機種・採点モード・キー変更・オクターブを構造化selectへ変更。直近4条件を表示し、「前回と同じ条件」1タップで4項目を本人確認できる。
- 比較時はper-recordingのuser-confirmed 4条件を優先し、旧E4のpair-level「同じ/違う」はlegacy/fallback evidenceとして維持する。`Original`/`原曲キー`/`0`などはcanonicalizationして比較する。
- 完全バックアップは10 store（R0の9 store + `pairContexts`）を保存する。
- `audio-analysis-worker.js` / `alignment-worker.js` はR0/F2から不変。

## R1実機確認の重点

1. DB6 upgrade後も既存の「眠り姫1 → 眠り姫」とpair-level採点条件確認が維持されること（D1再実行不要）。
2. A/B比較でR1 contextが `pairContexts` 由来として表示・exportされること。
3. 録音編集で日時を本人確認でき、2録音の日時が異なればpairボタンなしでもchronologyが成立すること。
4. 採点4条件を録音ごとに確認した場合、pair-level補助確認がなくても `confirmed_match` / `confirmed_difference_present` が成立すること。
5. R0完全バックアップ `songscope_full_backup_20260810T040901Z.zip` の災害復旧セルフテストがR1でも通ること（旧backup互換）。

---

## Audit R0 build 03 (frozen)
- `songscope-disaster-recovery-selftest-v2` の実機結果で `status=passed / verificationStatus=passed / cleanupStatus=deleted` を確認済み。
- empty temporary DB restore、全store件数、raw audio/DAM image SHA、JSON/binary一致まで検証済み。
- R1はこのR0バックアップ/復旧機構を維持する。

## Audit R0 build 02
- 通常の本番DBを変更せず、別名の一時IndexedDBへ完全バックアップを復元して全9 storeとbinaryを照合する「災害復旧セルフテスト」を追加。
- 復元transactionの失敗時に `store / primary key / error.name / error.message / transaction error` を記録する診断を追加。
- プライベートブラウズを災害復旧試験環境として使わず、通常Safari上の一時DBでempty-DB restore経路を検証できる。
- 本番restoreのmerge/atomic方針、完全バックアップschema `songscope-full-backup-v1`、DB_VER=5は変更なし。

## Audit R0 build 03
- build 02実機で、empty-DB restoreと全照合の後、一時DB削除だけが `blocked` となりテスト全体を失敗扱いしていたため修正。
- `dbAllFromConnection()` は `getAll().onsuccess` ではなくreadonly transactionの `oncomplete` まで待ってから返す。照合transactionが閉じる前にDBをdeleteするraceを除去。
- `deleteDatabase().onblocked` は即失敗にせず、connection解放後の同一request成功を待つ。一定時間残る場合のみcleanup warningとする。
- 復旧検証（空DBへのrestore＋全store/binary一致）と一時DB cleanupを別ステータス化。cleanupだけ失敗しても復旧検証を失敗へ格下げしない。
- self-test reportを `songscope-disaster-recovery-selftest-v2` に更新し、`verificationStatus` と `cleanupStatus` を別々に記録。
- 本番DB・完全バックアップschema・DB_VER・分析ロジック・workerは変更なし。


## R0実機検証手順

1. 更新後、ホームの **完全バックアップZIP** を押してZIPを保存する。
2. そのZIPをChatGPTへ送って内部構造・raw evidenceの同梱・SHA整合を監査する。
3. 可能ならSongScopeの **バックアップを復元** から同ZIPを選択し、検証後の確認画面で復元する。既存データは削除されない。
4. 復元後に録音数、DAM画像、構造化評価、E4/F1/F2が維持されていることを確認する。
5. **災害復旧セルフテスト** で同じバックアップを選び、`verificationStatus: passed` の結果JSONを書き出す。cleanupは独立項目として確認する。

---

# Base snapshot: SongScope v0.2 Phase F2（R0は分析ロジックを維持）

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
- Current Schema Version: `0.14.0`
- Current Build ID: `20260810-r1-01`


## Phase F2 — Repeated-direction Pattern evidence

### F2 build 01 — 3歌唱目からの保守的pattern抽出

- F1 build 02のphysical-recording正規化、chronology、source-verified outcome、scoring-condition chainをそのまま入力証拠として使います。Identityや順序をF2で再推測しません。
- 2 physical recordingsでは `waiting_for_third_physical_recording`。pair差は保持してもpatternへ昇格しません。
- 3〜4件のfully ordered / source-verified / comparable履歴で `exploratory_pattern_evidence_available`、5件以上で `repeated_observation_pattern_evidence_available`。これらは持続的な歌唱力向上/低下の証明ではありません。
- 各数値項目について隣接stepの `higher / lower / same`、回数、最長連続run、最初→最後のraw deltaを保存します。全隣接stepが同じ方向だった項目だけ `same_direction_observed_across_all_adjacent_steps` としてrepeated-signal候補へ載せます。統計的有意差や実質的意味の閾値は捏造しません。
- 技法回数・ビブラート量は `non_monotonic` のため、方向回数は記録してもrepeated better/worse signalから除外します。複合歌唱スコアやmetric重み付けも作りません。
- F2 ZIPは `pattern_summary.json` / `pattern_series.csv` / `history_snapshot.json`。raw音声・採点画像・D2 frame-level acousticsは含めません。
- F2は練習処方を出しません。将来のHypothesis / Practice層が、F2の繰り返しOutcome証拠と必要なD2区間観測・本人の体感を組み合わせるための入力を作る段階です。
- DB_VER=5、audio-analysis-worker / alignment-workerは変更なし。
- App: `0.2.0-phaseF2` / Schema: `0.13.0` / Build: `20260810-f2-01`


## Phase F1 — Same-song History / Progression evidence

### F1 build 02 — physical recording identity canonicalization

- build 01実機で、同じraw音声SHA-256を持つlegacy `recordingId` が複数残り、実歌唱2回を4 recordingとして数える問題を確認したため修正。Historyの件数は`recordingId`数ではなく**exact raw audio SHA-256で解決したphysical recording数**を使います。
- 同じSHA-256の複数recordingIdは1つのphysical recordingにcanonicalizeし、`canonicalRecordingId` / `aliasRecordingIds` / `sourceRecordingIds` を監査可能な形で残します。元recordは削除・統合しません。
- SHA未保存の旧recordでもIndexedDBのaudio blobが残っていれば、F1 export時にSHA-256を非破壊で計算して照合します。DBへは書き戻しません。
- SHAもraw blobも無くexact identityを確認できない旧recordは `identityResolution.unresolvedRecords` に隔離し、physical recording数・chronology・pattern readinessから除外します。recordedAtやduration一致だけでは同一音声と推測しません。
- E4 chronologyがlegacy aliasのrecordingIdを参照している場合も、alias→canonicalへ変換してphysical recording間の順序制約として利用します。同一physical recording内へ畳み込まれる制約は歌唱間chronologyとして扱いません。
- 同じexact raw音声のalias同士に異なるsource-verified構造化採点結果が存在する場合は `duplicate_alias_evidence_conflict` として止め、勝手にどちらかをtrendへ採用しません。
- F1 ZIPへ `history_identity_resolution.json` を追加。`history_outcomes.csv` にphysical recording ID、alias IDs、audio SHA、identity sourceを追加しました。
- DB_VER=5、D1/D2/E1–E4、audio-analysis-worker、alignment-workerは変更なし。
- App: `0.2.0-phaseF1` / Schema: `0.12.1` / Build: `20260810-f1-02`

### F1 build 01 — compact history package

- 同じ `songId` の**別recording**だけを履歴として束ねる `song_history.json` を追加。`analysisHistory` の再解析runは別歌唱として数えません。
- chronologyはE4のpair-level本人確認、user-confirmed recordedAt、日付が異なるsource-verified採点画像の日付を制約として集約します。複数の順序が可能なら `partially_ordered`、矛盾cycleがあれば `chronology_evidence_conflict_cycle` とし、無理に一列へ並べません。
- 完全に順序が定まった場合だけ、隣接録音間の採点条件comparabilityを連鎖として確認します。全stepがconfirmed sameの場合だけ `comparable_chain`。
- 2録音の差をtrendとは呼びません。3件以上のfully ordered / source-verified / comparableな履歴で初めて `exploratory_pattern_available`、5件以上で `repeated_observation_pattern_available` を許可します。これらも持続的な歌唱力改善の証明ではありません。
- `history_outcomes.csv` と `history_chronology.json` を同梱します。compact exportなのでraw音声・採点画像・frame単位D2は含めません。必要な監査は単体ZIP/比較ZIPに戻れます。
- 技法回数・ビブラート量はnon-monotonicのまま。F1ではD2のmixed-audio F0/RMSを履歴trendへ混ぜません。
- DB_VER=5のまま。`audio-analysis-worker.js` / `alignment-worker.js` は変更しません。
- App: `0.2.0-phaseF1` / Schema: `0.12.0` / Build: `20260810-f1-01`

## Phase E3 — pairwise outcome evidence

### E3 build 01 — structured scoring outcome comparison

- E2でsource-verifiedになった構造化採点結果を、A/B比較ZIP内で項目ごとに比較する `outcome_comparison.json` を追加。
- 比較対象は総合点、明示的に読めた採点metrics、技法回数、ビブラート、ハートボーナス等。欠損値は補完しない。
- 技法回数やビブラート量は増減を出しても「多いほど良い」とは扱わない。ランキングは母集団が変わりうるためraw deltaを作らない。
- `recordingId` と採点画像SHA-256が検証済みの構造化評価だけをOutcome観測に使う。source verificationと採点条件comparabilityを分離する。
- 採点条件の比較可能性は、機種・採点モード・キー・オクターブが双方で `user_confirmed` かつ一致した場合のみ `confirmed_match`。保存値が同じだけでは昇格しない。
- 両側評価が揃っていない場合も失敗せず、`waiting_for_second_structured_evaluation` など明示的な状態を出力する。
- 外部評価差とD2音響観測は自動で因果づけしない。総合的な「上達」判定もSongScopeでは行わない。
- DB_VER=5、audio-analysis-worker / alignment-workerは変更なし。

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
- 比較ZIPには `comparison_summary.json`、`comparison_windows.csv`、`metric_catalog.json`、`evaluation_anchors.json` を含み、Phase E3では `outcome_comparison.json` も追加します。
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
| `evaluation_anchors.json` | DAM等の外部評価証拠・provenance。画像や構造化評価が無い場合も状態を明示 |
| `evaluation/...` | 採点結果画像・抽出依頼JSON・source-verified構造化評価（存在するものだけ） |
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
3. ときどき「**完全バックアップZIP**」を書き出して、SongScopeとは別の場所へ保管する。
   - IndexedDB全store、raw audio、採点画像、full analysis、alignment dataを含む復元用バックアップです。
   - ZIP内部のCRC32に加え、復元時にraw audioと採点画像のSHA-256を再検証します。
4. 復元するときは「**バックアップを復元**」からSongScope完全バックアップZIPを選びます。既存データは消さず、同一IDのみ検証済みバックアップ内容で更新します。
5. ボイスメモ側の原本も引き続き残してください。完全バックアップとは別系統の原本保全になります。

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


## Phase E4 build 01 — Chronology / scoring-condition context

- A/B選択順と、実際の「先→後」を分離しました。タイトル末尾の数字、選択順、由来不明の同一recordedAtから順序を推測しません。
- 比較画面で「Aが先 / Bが先」を明示すると、pair-levelの本人確認として `alignmentResults.comparisonContext` に保存します。既存D1を再実行してもcomparisonContextを引き継ぎます。
- 採点条件は「機種・採点モード・キー変更・オクターブ」の4項目について、この2回で同じ / 違うをpair-levelで確認できます。recording metadataは上書きしません。
- per-recordingのuser-confirmed metadataとpair-level確認が矛盾する場合は `conflict_pair_report_vs_recording_metadata` として自動解決しません。
- source-verified採点結果が両側あり、時間順が確立すると、`outcome_comparison.json` に `progressionObservation` を追加し、A/B差とは別に `later - earlier` を保存します。これは外部評価の変化であり、歌唱力改善や原因を自動判定しません。
- 比較ZIPに `comparison_context.json` を追加しました。
- DB_VERは5のままです。新ObjectStoreは作りません。`audio-analysis-worker.js` / `alignment-worker.js` は変更しません。
- App: `0.2.0-phaseE4` / Schema: `0.11.0` / Build: `20260810-e4-01`


## Audit R1 build02
- DAMの「今回の総合点」と「自己ベスト」を別の証拠として扱えるようにし、source-verified画像由来overallScoreと本人確認済み手入力DAM点数が不一致なら `conflict_manual_score_vs_source_verified_image` として手入力点差をblockします。
- external evaluation requestは、画面上で明示的に読める場合のみpersonalBestをoverallScoreとは別に抽出するよう要求します。
- chronologyは `exact datetime / date-only / relative-order-only / unknown` の精度を区別します。正確な時刻が分からなくても、日付だけ、またはpairの相対順序だけで履歴を保持できます。
- `personalBest > SongScope内の観測済みoverallScore最大値` は `historyCompleteness.may_omit_unrecorded_takes` という警告にだけ使い、chronologyやpatternを自動で変更・blockしません。


## G0 — DAM画像の離散観測（2026-08-11）
- G0はObservation層のみ。練習提案・原因推定・take間の良否判定は行わない。
- 外部画像抽出requestに、ロングトーン上手さ、ビブラート上手さ、安定性、リズム、声域、音程グラフの可視エラーマーカー、分析レポート文の任意フィールドを追加。
- 数えられる表示だけを数える。グラフやバーから隠れた数値・百分率を逆算しない。
- 音程グラフの横位置は graphical_only の0..1近似位置としてのみ保持でき、G0では音声時刻へ変換しない。
- 既存 `songscope-external-evaluation-v1` とDB_VER=6を維持し、過去の評価JSON/データを壊さない。


## G0 build02 — DAMデンモク multi-image evidence set
- G0の正式入力源を `dam_denmoku` に限定。カラオケ端末の直撮りは当面対象外。
- 1採点結果を1枚ではなく `evaluationEvidenceSet` として扱い、精密採点DX-Gのような複数画面を1つの証拠セットに束ねる。
- 画像はSHA-256で個別識別。既存の単一画像データは自動的に1枚セットとして後方互換。
- extraction request v2は全画像SHA集合を要求し、外部構造化JSON v2は全画像集合が一致した場合のみsource_verified。
- `scoringPerformedAt` はDAMデンモク表示の採点日時として扱い、iPhone `recordedAt` とは分離。
- 精密採点Ai / 精密採点DX-Gの違いは欠損を推測で埋めず、共通値＋mode-specific/discrete observationsとして保持する。


## G0 build03 (2026-08-11)
- DAMデンモク採点履歴を録音から独立した一次証拠として保存する `scoringEvidenceSets` store を追加（DB_VER 7）。
- 1採点結果を1〜複数画像の evidence set として保存し、録音とのbindingは未確認のまま保持可能。
- 未紐付けevidence setはホームから抽出ZIPを書き出せる。外部AIにはrecordingIdを推測・付与しないよう要求する。
- 従来の録音画面からの画像添付は「同一歌唱だと確認済みの場合」の直接binding経路として残す。


## G0 build04
- iOS SafariでDAMデンモク採点履歴画像を選択後、一覧が更新されない不具合を修正。
- file inputをresetする前にFileListをArrayへsnapshotし、非同期保存へ渡す。
- DB schema/worker/評価意味論は変更なし。


## G0 build05
- 独立したDAMデンモク採点証拠セットの抽出ZIPで、画像Blobを直接ZIP writerへ渡さないよう修正。
- 各画像を `Blob -> ArrayBuffer -> Uint8Array` に変換し、保存済みfileSize / SHA-256と再照合してからZIP entryを生成。
- `zip.js` は string / ArrayBuffer / TypedArray 以外を拒否し、Blob等の未対応型がheader size=0の不正ZIPを黙って生成する経路を遮断。
- BUILD_ID: `20260811-g0-05`。


## G0 build07
- iPhone-first DAM scoring evidence layout.
- Audit-critical evidenceSetId, binding status, source verification, and user review are no longer ellipsized.
- Evidence actions use a responsive 2-column grid (1 column on very narrow screens).
- No evidence model, binding semantics, or scoring extraction semantics changed.


## G0 build08 — Audit Safety Gate
Claude再監査（2026-08-11）のBlocking findingsを受け、Performance/Binding実装前の安全性修正を実施。

### B-01 gate
- 録音レビュー画面から旧 `evaluationEvidenceImages` / `evaluationStructured` へ新規追加・削除するUIを停止。
- 旧write関数もbuild08では明示エラーにし、新規データはホームの独立 `scoringEvidenceSets` だけへ入る。
- 既存legacy証拠は削除しない。build09で非破壊移行する。

### B-02 schema v2 / review
- `songscope-external-scoring-result-v2` を導入。
- 全requested fieldに `fieldStatus` を必須化:
  `extracted / not_visible_in_images / unreadable / visible_not_extracted / not_applicable`。
- `null`だけでは欠落理由を表現できないようimport validatorを強化。
- countableな離散状態（安定性・ロングトーン・ビブラート・リズム等）はObservationとして数えられることを抽出ルールへ明記。
- iPhoneレビューsheetでraw画像と全fieldの抽出値/statusを同時表示してからuser reviewを保存。
- `valueReviewStatus` と `coverageReviewStatus` を分離。
- `visible_not_extracted` が存在する場合は `user_confirmed_with_known_gaps`。
- v1の過去reviewは削除しないがUIでは `legacy_review_needs_reverification` として再確認を要求。

### B-05 scoringPerformedAt
- schema v2では裸のoffset-less ISO文字列を禁止。
- `{localDateTime,timeZone,precision,source}` として保存。
- DAM画面にtime zone/offsetが表示されない限り `timeZone:null`。JST等を抽出時に推測しない。

### B-04 delete lifecycle
- 独立scoring evidenceの通常「削除」を廃止し、raw bytesを保持する `archived` へ変更。
- archiveの表示/復元UIを追加。
- 録音削除時、そのaudio SHAを含む`pairContexts`のchronology/scoringConditionsをunknownへ無効化し、
  `invalidatedAt` とhistoryを残す。同一音声を再取り込みしても古いuser confirmationが自動復活しない。

### B-10 source verification
- SHA集合だけでなく `imageId ↔ SHA-256` ペア集合が完全一致した場合だけsource verificationを通す。

### B-08 PWA update
- waiting Service Workerを検知するとiPhone上に更新バナーを表示。
- ユーザーが「更新する」を押した場合だけ `SKIP_WAITING` → controllerchange → reload。
- 実行中ページと新workerのversion skewを避ける方針は維持。

### Scope
- DB_VERは7のまま。新しいbinding store/Performance entityはまだ作成していない。
- F1/E3/Observed Historyの旧consumer一本化はbuild09で行う。


### build08 static/validator checks
- app.js / service-worker.js: Node syntax check PASS.
- structured scoring v2 fixture: validator PASS.
- imageId↔SHAを入れ替えたfixture: import rejection PASS.
- fieldStatusを1項目欠落させたfixture: import rejection PASS.
- scoringPerformedAtを旧裸文字列へ戻したfixture: import rejection PASS.
- v1 stored result: source bindingは保持しつつ `legacy_review_needs_reverification` へ降格することを確認。


## G0 build09
- iPhone Safariの採点レビューでIndexedDB Blobのblob: URL表示が失敗するケースを回避。
- レビュー表示時にraw image bytesのsize/SHA-256を再検証し、MIMEを明示したData URLで表示。
- raw画像が表示・検証できない場合はuser confirmationを無効化。
- review sheetをVisual Viewport基準へ変更し、Safariのアドレスバー/ツールバー下への潜り込みを抑制。
- レビュータイトル/閉じるをsticky化。
- scoring schema / evidence semantics / Binding設計は変更なし。


## G0 build10 — Scoring Evidence Unification / B-01
- 旧recording-attached採点画像・structured JSONの新規入力停止を継続。
- 既存旧証拠をraw bytesのSHA-256再検証後、`scoringEvidenceSets`へ非破壊移行。
- 旧入力経路はsource種別を実際には強制していなかったため、移行データを`legacy_recording_attachment_unclassified`として保存し、`dam_denmoku`へ勝手に再分類しない。
- 「昔このrecordingに添付されていた」事実は`legacyAttachmentCandidates[]`へ保存するが、`bindingStatus=unbound / boundRecordingId=null`を維持。same-performance Bindingとは扱わない。
- legacy bytes/JSONはaudio storeにもread-onlyで残し、監査・rollback可能性を維持。
- build10以降、recording export / D2 / F1 の採点証拠consumerは`scoringEvidenceSets`を参照し、旧audio-row評価フィールドを直接消費しない。
- legacy candidate由来の採点値は、明示Binding前はObserved Historyの数値系列・E3比較へ使用しない。
- DAMデンモクとして正式に追加した独立evidence setと、旧方式source未分類setをUIで区別。


## G0 build11 — Pre-Binding audit closure
- F1 `historyCompleteness` をR2 Observed Historyへ明示伝搬。
- personalBest等から未観測takeの可能性が検出された場合、R2に`history_may_omit_unrecorded_takes`警告を保持。生成自体は止めず、「SongScopeへ取り込まれた観測列」に限定して解釈する。
- DAM値の`displayResolution`をR2 metric patternへ追加。これは画面表示の粒度のみを表し、技能変化の`minimumMeaningfulDelta`としては使用しない。
- 各adjacent stepへ`deltaInDisplaySteps`と`isSmallestNonzeroVisibleChange`を追加。
- recording削除時、同じaudio SHAの別recordingが残っていない場合だけ、関連`pairContexts`を監査履歴付きで無効化。
- 無効化contextはF1 chronology/scoring-condition evidenceから防御的に除外。
- 同じ音声を後日再取り込みしても古い確認は自動復活しない。A/B画面で新たに明示確認した場合だけ`reactivated_by_new_explicit_user_confirmation`として再有効化。
- Binding/Performance entityはまだ実装しない。


## G0 build12 — History completeness semantics
- `historyCompleteness`で「評価できない」と「missing take signalが無い」を分離。
- eligibleなsource-verified/bound outcomeにpersonalBestが無い場合は`not_assessable_no_eligible_personal_best_evidence`。
- eligibleなoverallScoreが無い場合は`not_assessable_no_eligible_observed_score`。
- personalBestとobserved scoreの双方がeligibleな場合だけ`may_omit_unrecorded_takes` / `no_missing_take_signal_from_personal_best`を評価。
- R2 Observed Historyへassessment statusとsignal statusを別々に伝搬。
- `not_assessable`は`no_missing_take_signal`として扱わない。
- unbound/legacy candidate証拠をcompleteness判定へ黙って流用しない。ただし「除外された証拠が偽」という意味ではなく、将来の独立history/completeness evidence layerで扱う余地を明記。


## G0 build13 — Append-only Binding Assertions
- DB_VER 8。`bindingAssertions` storeを追加し、完全backup/restore/self-test対象へ含める。
- Binding対象はmutableなrecordingIdではなく、exact raw audio `audioSha256`。recordingIdは確認時のUI参照としてassertionに併記。
- `bind` / `unbind` は追記専用。過去assertionを上書き・削除しない。
- `scoringEvidenceSets.bindingStatus` / `boundRecordingId` はlegacy compatibility fieldへ降格。current Bindingはassertion履歴から毎回導出。
- 1 scoring evidenceが複数audio SHAへactive bindされた場合は`binding_conflict`としてOutcome利用を停止。
- 同一raw audio SHAに複数scoring evidence setが明示Bindingされた場合も、duplicate解決までは`ambiguous_multiple_bound_scoring_evidence_sets`としてOutcome利用を停止。
- iPhone向けBinding管理sheetを追加。候補は最大3件、検索可能、候補表示だけではBindingしない。
- 候補順位に使えるのはuser-reviewed/source-verified structured resultと録音metadataの一致。`scoringPerformedAt`はtimezone未確定のため表示のみで候補順位には使わない。
- user confirmation時に`basisShownToUser`とraw audio SHAを保存。
- Binding撤回は`unbind` assertion追記。履歴は残る。
- recording export / scoring evidence export / D2 exportにBinding assertion履歴とderived stateを含める。
- F1/R2は、`dam_denmoku` + current schema + source_verified + user review + explicit Bindingが全部成立したstructured resultだけを録音Outcomeとして扱う。
- structured scoring result v2の音程/表現力/抑揚/聴感、ロングトーン/ビブラート上手さ/安定性の離散表示、リズム位置、技法回数、ビブラートをObserved Historyへ変換可能にした。リズム位置・技法量・ビブラート量はnon-monotonicのまま。
- Performance entity / performanceId永続storeはまだ作らない。


## G0 build14 — R2 missing-delta semantics
- `f2DirectionFromDelta`で`null / undefined / empty string / non-numeric`を明示的に`unknown`へ分類。
- JavaScriptの`Number(null) === 0`による「未観測 → same」の誤変換を禁止。
- missing deltaでは`deltaInDisplaySteps = null`、`isSmallestNonzeroVisibleChange = false`。
- `directionCounts.unknown`へ集計し、`same`へは加算しない。
- `unknown`はcomplete adjacent directionとして扱わず、longest direction runにも含めない。
- `pattern_series.csv`へ`unknown_step_count`列を追加。
- R2 schemaを`songscope-observed-direction-history-0.5.0`へ更新。
- Binding Assertion設計・DB schema・scoring evidence semanticsは変更なし。


## G0 build15 — Normal-use workflow shell
- データモデルは変更せず、ホーム画面を「通常利用」と「データ管理・監査」に分離。
- 通常利用の主操作を `① ボイスメモから録音を取り込む` / `② DAM採点画像を取り込む` の2つへ集約。
- 保存状態から「次にすること」を自動判定し、レビュー・Binding・次の録音追加へ直接案内。
- evidenceSetId / SHA / source verification / archive / backup / JSON等は通常画面から外し、「データ管理・監査」detailsへ退避。
- 未構造化の採点画像だけは現開発版の制約として、通常statusから「解析用ZIPを作る → 返ったJSONを読み込む」の一時導線を表示。最終通常UIでは隠す対象。
- 録音入力フォームの詳細欄を「必要なときだけ追加」に変更。手入力DAM点数は旧入力・基本不要と明記。
- 機種/採点モードは画像から取得できる場合は手入力不要と明記。
- 目標通常運用: 録音 → DAM画像 → 必要時のみ人間確認。監査データは裏側で保持する。


## G0 build16 — Daily operation route
- ホームの主導線を2ボタン常設から「今回のカラオケを取り込む」1本へ変更。
- カラオケ中はSongScopeを触らず、ボイスメモ＋DAMを通常利用する前提。
- カラオケ後にsession intake sheetを開き、録音→DAM画像を追加。順番は任意。
- 取り込み後は「いま必要なこと」にレビュー/録音対応/暫定AI読み取りなど、次の1操作だけを表示。
- 通常UIでは`Binding`用語を「どの録音か確認」「対応済み/未確定」へ置換。append-only assertion構造自体は変更しない。
- audit detailsではevidenceSet / SHA / source verification / Binding assertion等を引き続き保持。
- 開発中の外部AI抽出だけは「ChatGPTに渡すファイルを作る → 読み取り結果を戻す」という暫定導線。
- 録音フォームはファイル名を初期曲名として自動入力し、詳細条件は折りたたみ。今後はscoring evidenceから安全に補完できるメタデータをさらに手入力から外す。


## G0 build17 — iPhone Safari sheet scroll stability
- build09で導入した`visualViewport.offsetTop/offsetLeft`追従を停止。
- Safariのアドレスバー/ツールバー伸縮に伴うVisualViewport scrollイベントで、上スワイプ時にmodal sheet全体が下へ移動する不具合を修正。
- modal geometryは`100dvh`へ一本化し、fixed wrapperを`inset:0`へ固定。
- sheet内部へ`overscroll-behavior: contain`、wrapperへ`overscroll-behavior: none`を追加し、nested scrollのbackground/browser側への連鎖を抑制。
- sticky header / raw evidence review / Binding / daily session intakeのデータモデルと意味論は変更なし。


## G0 build18 — Safari internal sheet scrolling
- build17でsheet位置暴走は停止したが、`100dvh`固定だけではSafari実表示領域と合わず、sheet内部がscrollせずgestureがrootへ漏れてpull-to-refreshになる実機症状を修正。
- `visualViewport`は`height/width`だけ使用。`offsetTop/offsetLeft`は引き続き一切使用しない。
- sheet open中は背面documentをposition fixedでscroll lockし、close時に元scroll位置へ復帰。
- sheet wrapperをvisible viewport heightへ合わせ、sheet本体だけ`overflow-y:auto`でscroll。
- touch boundary guardを追加し、sheet先頭から下へ引く/末尾からさらに上へ引くoverscrollだけpreventDefault。通常の縦scrollはnativeのまま。
- Safari pull-to-refreshへgestureが漏れないことを目的とする。
- データモデル・Binding・evidence semantics・daily workflowは変更なし。


## G0 build19 — Native sheet scrolling
- build18のtouch boundary guardを撤去。Safariの`touchmove`をJavaScriptでpreventDefaultしない。
- 背面documentのscroll lockだけを維持し、modal sheet内部はiOS Safari標準のnative scrollへ戻す。
- sheetを`visualViewport.height - 12px`の固定client heightにして、contentが長い場合に必ず`scrollHeight > clientHeight`となる構造へ変更。
- `overflow-y: scroll` / `-webkit-overflow-scrolling: touch`を明示。
- visualViewportはheight/widthのみ利用し、offsetTop/offsetLeftは使用しない。
- データモデル・daily workflow・Binding/evidence semanticsは変更なし。


## G0 build20 — hidden modal regression fix
- build19で`.sheet-wrap { display:flex !important; }`を追加したため、既存の`[hidden]{display:none !important}`より後勝ちし、modal wrapperが閉じていてもgray overlayだけ常時表示される回帰が発生。
- `.sheet-wrap`から`display:flex !important`を撤去。
- 最終CSSに`.sheet-wrap[hidden]{display:none !important}`を追加し、hidden stateを防御的に固定。
- build19のnative Safari sheet scrolling方針自体は維持。
- データモデル/Binding/evidence semantics/daily workflowは変更なし。


## G0 build21 — UI Platform Stabilization
- build09/17/18/19/20で累積していた`.sheet` / `.sheet-wrap`のviewport・scroll上書きを削除し、canonical implementation 1系統へ統合。
- modal open時に`visualViewport.height`を1回だけ取得して`--songscope-sheet-vh`へfreeze。通常のSafari toolbar伸縮では再計算しない。
- `visualViewport.offsetTop/offsetLeft`は使用しない。
- ソフトウェアキーボードでsheet内input/textarea/selectがfocus中の場合だけvisualViewport resizeに追従。
- orientation change時だけviewport heightを再取得。
- 背面documentはsheet open中だけfixed scroll lockし、close時に元のscroll位置へ復帰。
- sheet本体を唯一のvertical scroll containerにし、`overflow-y:auto` + `overscroll-behavior-y:contain`。JavaScriptのtouchmove/preventDefaultは使用しない。
- 全sheet headerをstickyに一本化。
- transform slide animationを削除し、scroll/stickyとの干渉要因を除去。
- hidden stateは`.sheet-wrap[hidden]{display:none !important}`で一意に保証。
- データモデル・Binding・evidence・daily workflowは変更なし。
