# 親機軸合わせのPPS UTC未成立判定修正（2026-10-28）

## 前提
- ユーザー申告：GPS PPS同期中にも親機の軸合わせで「PPSによるUTCが未成立」と表示される。
- このフォルダはGit管理のチェックアウトではないため、Git差分は利用できない。元の隣接AquaBeaconは読取りのみ。
- 実機操作・USB書込み・PCのWi-Fi切替・SDフォーマット・既存ログ削除なし。親機温度/水圧/LCDは対象外。

## 原因と実施
- `bodyStartIssues()` / `bodyClockReady()` は `selectedUtc` のコピーを参照していた。GNSS/PPSをコア1が更新し続けても、SD/I2C等でコア0の `utcTick()` が遅れると、その古いUTC参照は期限切れになる。最新GNSSの同期成立と軸合わせの判定が食い違う経路を確認した。ユーザー実機で発生した個々の瞬間を採取したものではない。
- `utcSnapshot()` は最新GNSSスナップショットからPPSアンカーを生成して優先する。GPS無効時は保存済みGPSアンカーを返さない。RTC/端末時計の一般記録経路を維持し、軸合わせでは引き続きGPSを必須とする。
- UTC選択・Spresense送信時の現在時刻はGNSSスナップショット取得後に読む。別コアの更新が取得前の時刻を追い越した場合の誤拒否を回避する。
- 軸合わせの開始・継続判定、イベント記録の単調時刻もスナップショット取得後に読む。
- ピン定義と隣接 `AquaBeacon/pcb/build_parent_main.py` / `build_child_main.py` を読取り照合。旧生成スクリプトの単方向EVENT表記よりユーザー確認済み配線を優先し、GP6入力・D02入力専用・GP7↔D03半二重の実装は変更しない。
- READMEとdocs/spec.mdを同時更新。docsファイル増減なし。

## 実測（ソフトウェア検証）
- `tests/test_parent_live_utc.py`：実際の `utcSnapshot()`・`gnssLocked()`・`bodyClockReady()` を抽出してコンパイル実行。古いGPSキャッシュ失効・未設定・RTCキャッシュ時に、最新GNSS/PPSが有効なら時刻条件成立を確認。
- 別コアのスナップショット時刻更新、GNSS同期不成立、GNSS状態更新100ms失効、PPS1.5秒失効、未来の受信時刻、診断用GPS除外、RTC/端末時計だけの場合、Spresense独自条件の不成立も検査し、拒否を確認。
- `../P_MAIN_experiment/.venv/Scripts/python.exe scripts/test_host.py`：全体ホスト試験PASS、終了コード0。実行ログは下記参照。禁止された実機Wi-Fi切替テストは含めていない。
- `../P_MAIN_experiment/.venv/Scripts/pio.exe run`：parent / child100ともSUCCESS。親機RAM 394884/524288 bytes、Flash 672672/4190208 bytes。子機RAM 287080/524288 bytes、Flash 445224/4190208 bytes。
- 通常の `python` にはziglangがなく初回起動時に失敗。既存の実験用仮想環境のPythonで再実行した。

## 未検証
- 続報：ユーザーのUSB接続後に親機書込み・照合とUSB状態確認を実施。[実機反映記録](../2026-10-28_004_parent_pps_deploy/README.md)を参照。以下は修正作業完了時点の未検証事項。
- 実機書込み、実機Webの表示・開始応答、長時間の姿勢収録、SD負荷中の同期維持。
- PPSラベルの秒対応、絶対UTC・軸・距離精度。今回のテスト通過を精度合格とは扱わない。
- 親機更新後は通常記録とSpresense記録が有効な状態で手順5の不足条件を再確認する。PPSまたはSpresenseの条件が実際に不成立なら開始は拒否される。

## 生ログ
- `../raw/2026-10-28_003_parent_pps_utc/host_tests.log`
- `../raw/2026-10-28_003_parent_pps_utc/build.log`
- 回帰試験の生成C++と実行ファイルは `../raw/test_parent_live_utc.*`。
