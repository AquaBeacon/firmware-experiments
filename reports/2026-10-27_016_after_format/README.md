# フォーマット後の校正復元・連続保存再確認

## 前提
- 2026-10-27 JST。ユーザーが同じSDをフォーマットし、Spresenseへ戻したと報告。カード本体の表記容量の回答はないため、実測値は認識ボリューム容量として扱う。
- PC Wi-Fi切替、エージェントによるSDフォーマット、既存ファイル削除、ファーム書込みなし。
- Spresense USB 10878C89E6DBED1197F5F12D62C613AC / COM7とIMU/LINK/pps_input=D02、親機USB A444A41EE9334705 / COM6とP_MAIN応答を照合。
- GP6=外部GNSS PPS入力、D02=PPS入力専用、GP7–D03=半二重を維持。親機温度/水圧/LCDは対象外。元リポジトリ/SDKは未変更。

## 実測：形式と空き
- SD_SPACE total_bytes=31925993472、free_bytes=31925895168。空き約31.926GB、使用98304byte。
- MBR signature=aa55、type=0c、LBA=2048。BPBは512byte/sector、32sector/cluster、FAT2面、FAT32 sectors=15224。
- フォーマット前と総領域・形式・クラスタサイズは同じ。今回の媒体はFAT32として認識できた。
- cの一覧完了を確認し、校正CALファイルは0件。フォーマット前の校正値は動作中RAMと先行013のPC控えに残っていた。

## 実施：校正係数・参照番号の復元
- 初回親機照会では既にSTART(3)/recording=trueを観測。停止条件のassertが成立しなかったため、その段階では保存処理を行わなかった。その後Spresense qでSTOPPED_REMOVE_SDを確認。
- 既存の停止中保守コマンドCAL ENABLE_SAVEDを使用し、RAMの有効係数を新規保存。既存persistCalibrationがカード上の最大番号+1を割り当てる仕様のため、空カードから1→2→3の3世代を作成し、親機セットが参照する番号3へ戻した。
- 各段階でUSB cから全64byteを読戻し、形式/CRC/有効状態と、世代番号・CRCを除く全バイトがPCの番号3控えと同じことを確認してから次へ進んだ。最後のK00003.CALは控えと全64byte一致。係数の再測定・変更なし。
- 作成したK00001.CAL/K00002.CAL/K00003.CALは全て同じ有効係数。今回の番号2は新規の有効レコードであり、以前削除した無効世代の復元ではない。既存ファイルの削除/上書きなし。
- K00001.CAL SHA256=3d374fbe80f5b5a88b9f53c6149e949a1296ed8c16b486c3be0463a0e3e818eb
- K00003.CAL SHA256=799b9ed542022a618f311ce1f54062df875d104a5b867093160949b245510dcc

## 実施：再起動復元
- 親機から新鮮なSpresense停止完了を確認後、既存@SPR 4でSpresenseだけを再起動。
- 親機の受付ID2を照合、サンプル数3556812→2300への低下で再起動を確認。SDから校正番号3を復元・適用し、calibration_restore_error=0、recording=true/sd_ok=true/sd_errors=0を確認。
- ソース・両コアSPKのSHA256は先行013の最終版と一致。今回はソース変更・ビルド・ファーム書込みなし。既存実装の実機確認であり、ホスト試験/ビルド結果は013を参照。

## 連続記録・回収
- 180秒の観測窓で178件の状態を取得。最初〜最後の状態の時刻差178.295秒、保存カウンター59443→231817（増加172374件、参考時刻行を含む）。全状態sd=1、SDエラー/IMUエラー/IMU欠落/IMUキュー廃棄/参考時刻キュー廃棄は最初から最後まで0。カウンターの巻戻り・再起動なし。
- 上記の長いログは全量をUSB回収していない。継続書込み・同期済み件数の増加を状態で確認した試験。
- 続いて安全停止→新規ペアで約4秒記録→安全停止→USB i/gで実ファイルを回収。
- IMUは505728byte＝512byteヘッダー＋3947×128byte。全3947件のCRC・連番（欠落0）・校正番号3と補正値・時刻条件を検証。品質分布{2: 3947}。時刻不確かさは未測定UINT32_MAXのまま。
- 参考時刻は640byte＝ヘッダー＋1レコード。外側CRC、内側AQB1 CRC、形式を検査。参考時刻情報はsummary.jsonを参照。実機の参考時刻レコードも初めて読戻し検証できた。
- 回収後に新規ペアで保存を再開し15秒以上観測。さらに親機USBでlink_fresh=true、Spresense recording=true/sd_ok=true/sd_state=RECORDING/sd_failure=NONE/sd_errors=0、sd_rows=295534・sd_synced_rows=295118、IMU欠落0を確認。**Spresenseは記録継続中。**
- 親機セット番号3はSpresense校正番号3と一致し、保存/復元エラーなし。親機自体のSDはSTOPPEDで、今回親機の記録開始操作は行っていない。
- 最終のSpresense PPS入力は検出、IMU時刻準備済みだがPPS/UTC対応はfalse。記録試験中にUTC品質が成立した区間があることと、常時成立・絶対同期精度の保証を混同しない。

## 判断・未検証
- フォーマット・差し直し・再起動後は、この観測範囲でWRITE/110が再発しなくなった。短時間保存の改善は確認したが、根本原因特定・恒久解消とは扱わない。
- 同じ容量/形式/ファームのまま、フォーマット・差し直し・再起動後の保存を比較する。改善しても、容量そのものやFAT管理情報・データ配置・接点等のどれかを原因と断定しない。
- 約4GB使用後の再発有無、全領域の書込み・読戻し、256MiB分割境界、長時間記録、物理電源断は別途未検証。
- 同期/距離/姿勢の絶対精度は未測定。PPS/UTC対応フラグだけを精度合格としない。実機Webはユーザー操作、こちらでは実施していない。

## 証跡
reports/raw/2026-10-27_016_after_format以下。usb_readonly.txt/read_only_result.json、parent_before_restore.json、restore_usb.txt/restore_result.json/restored_K*.CAL、reboot_parent_usb.txt/reboot_result.json、same_firmware.json、recording_usb.txt/recording_states.json/recording_result.json、short_imu.bin/short_reference.bin、parent_final.json、summary.json。
