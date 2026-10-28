# 交換用SDなしでのSpresense読取り確認

## 前提
- 2026-10-27 JST。ユーザーが、約4GBはSpresense SDの保存済みデータ量であること、交換用カードがないことを回答。
- Spresense USB番号10878C89E6DBED1197F5F12D62C613AC / COM7と、IMU/LINK/pps_input=D02応答を照合。
- 今回は追加の記録開始、ファーム書込み、SDへの試験ファイル作成、フォーマット、修復、既存ログ/校正の削除なし。PC Wi-Fi切替・親機操作・実機Web操作なし。

## 実施
- USB応答で記録停止を確認後、既存のv診断でstatfs・MBR/BPBを読取り。
- USB iで現在のIMUログを2回読み出し、それぞれPCの新規ファイルに保存。AQSBIN01ヘッダー・各レコードのCRCをデコーダで検査し、SHA256を比較。
- 通常ロガーとSony Arduino core 3.4.7のSDHCI.cppを読取り、復旧の処理範囲を確認。ソース変更なし。

## 実測
- 記録領域31925993472byte、空き26995081216byte。空き不足による停止ではない。
- MBR signature=aa55、partition type=0c、partition LBA=2048。BPBは512byte/sector、32sector/cluster、FAT2面、FAT32 sector count=15224。
- 直近IMUログは90112byte・700サンプル。2回とも読取りとCRC検査が成功し、互いに同一。前回013で回収したファイルともSHA256一致。
- SHA256: e85642312d80d49dd294e1f6500fb4cd7ac8ab00795336b6d412341c6cf0c8a4
- 最終もrecording=0。追加の保存開始要求なし。

## 復旧処理の確認
- loggerのserviceSdRecovery/resumeRecordingはopenLogsを呼び、新規試験ファイルの書込み・同期・読戻し後に新規ログを開く方式。
- SDHCI.beginは/mnt/sd0の存在をstatで待つだけ。現在のロガーからSDブロックデバイスの再初期化・電源再投入・アンマウント/再マウント・ファイルシステム修復は行っていない。
- 従って「復旧成功」として新規ファイルへ再開しても、SD/給電/ドライバー等の状態が残れば同じ書込みタイムアウトが再発し得る。今回の再発原因がどれかは未確定。

## 未検証・次の切り分け
- 成功した読取りは直近の小さいログのみ。既存約4GB全量の整合性、全クラスタ/空き領域、媒体の書込み健全性を証明していない。
- 前回のWRITE/110の根本原因、SDの制御系の完全な再初期化、接点・電源波形、別媒体比較は未検証。
- ユーザーへPCで同じカードを読み取れるカードリーダーがあるか確認中。可能なら既存ログを先にバックアップし、修復や削除を伴わない検査を行う。交換用カードがないことだけでカード不良と断定しない。
- 同期/距離/姿勢の精度検証は今回の対象外。

## 証跡
reports/raw/2026-10-27_014_same_card_diagnosisのread_only_usb.txt、read_only_result.json、export_1_usb.txt、export_2_usb.txt、readback_1.bin、readback_2.bin。
