# 親機PPS UTC修正版の書込み・USB確認（2026-10-28）

## 前提
- ユーザーの「接続しました」を受け、直前に作成・ビルド検証したPPS UTC修正版を親機へ反映。
- USB番号A444A41EE9334705、COM6、実機JSONのrole=P_MAINの両方で識別。子機へは書き込まない。
- PCのWi-Fi切替、実機Web操作、SDフォーマット・既存ログ削除なし。親機温度/水圧/LCDは対象外。

## 実施
- USBから書込み前の状態を6秒取得。
- 既存のscripts/flash.py parentを使用。識別後に測距・親機記録を停止し、停止確認後に親機ビルド・書込み・フラッシュ照合・再起動。
- USB再接続後、45秒間hによる状態照会のみでPPS/UTC・Spresense・軸合わせの開始診断・SD状態を観測。

## 実測
- 書込み前：親機GPS PPS UTC有効、Spresense通信/記録/SD/IMU/PPS対応/UTC/IMU時刻が成立。校正番号3を適用し親機校正セットと一致。
- 書込み前のbody_checkはx=0、l=32768、z=3。現在は開始可能だが、直前の姿勢収録は親機UTC不足の理由で中止された履歴が残る。ユーザー申告と整合するが、その瞬間の原因を直接採取したものではない。
- 親機upload SUCCESS、フラッシュ照合100% OK、再起動を確認。
- 再起動初期はSD INITIALIZINGとSpresense PPS対応待ち。起動後約23秒の状態ではSD NONE、親機gps_pps_candidate有効、Spresense PPS/UTC成立、body_check.x=0、l=0となった。
- 個別校正番号3と適用状態を保持。親機の校正参照一致を確認。姿勢・カメラ収録や補正値の保存・変更は行っていない。
- 45秒間で状態79件、GNSS同期成立65件。その65件で親機UTC不足bit32768の検出は0件。開始条件x=0は48件。最終もx=0/l=0、SD NONE、sd_errors=0、UART overflow=0、親機/SpresenseのPPS UTC成立。

## 未検証
- ユーザー操作による実機Webの手順5開始応答、実際の4姿勢と動作収録の継続、軸変換解析・保存。
- 長時間・高SD負荷時の再発有無、PPSとUTCの秒対応、絶対時刻・姿勢・距離精度。
- 短時間のUSB状態確認を、軸合わせ完了や精度合格とは扱わない。

## 生ログ
- reports/raw/2026-10-28_004_parent_pps_deploy 以下に before/after.jsonl、状態要約、flash.log、observe.log を保存。
- 状態には無線設定の情報を含むため、全文を本文へ転記しない。
