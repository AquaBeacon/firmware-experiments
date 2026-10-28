# フォーマット後の容量・形式の確認

## 前提
- 2026-10-27 JST。ユーザーがSDカードをフォーマット済みと報告し、容量が大きいこととの関係を質問。フォーマットはユーザーの操作であり、エージェントは実施していない。
- 前回の既存約4GB全量のバックアップは、PC上に対象カードが現れなかったため未実施。PCには先行013で回収した直近ログ700件と校正K00001.CAL/K00003.CALが残る。
- 今回もファーム書込み・SDフォーマット・修復・削除・記録再開なし。PC Wi-Fi切替なし。

## 実施・実測
- PCのディスク/ボリューム一覧には内蔵NVMeとC:のみ。フォーマット後SDの容量・形式はPCから取得できなかった。
- Spresense USB番号10878C89E6DBED1197F5F12D62C613ACとIMU/LINK/pps_input=D02応答を照合。初回recording=0。
- v/cの読取り診断を要求したが、観測窓内にSD_SPACE/SD_BOOT/SD_BPB/CAL_FILES_ENDは取得できなかった。これだけで媒体故障やSDシステムコール停止と判定しない。現在のカード挿入先も未回答。
- 後続のUSB状態は通常どおり取得。qで停止完了STOPPED_REMOVE_SDとrecording=0を確認。記録開始要求は送らない。古いWRITE/110のカウンターをフォーマット後の新規失敗と取り違えない。
- PC上の校正番号1/3の控えを形式・CRCで検査し、両方有効。番号3 SHA256: 799b9ed542022a618f311ce1f54062df875d104a5b867093160949b245510dcc。カードへの復元は未実施。

## 仕様と判断
- Sony公式Arduinoガイド2.13節：SD/SDHC、最大32GB、FAT12/16/32対応、exFAT/SDXC非対応。
- 先行のstatfs約31.9GBは認識済みボリュームの大きさ。カード本体の表記容量やSDHC/SDXC種別を直接確認したものではない。大容量カードに32GBのパーティションを作った場合まで対応と推定しない。
- FAT32の約4GiB制限は1ファイルの上限であり、保存済み全ファイルの合計4GBとは別。
- 先行013では新しい約90KBのログでもWRITE/110が発生した。その再発は単一ファイルが4GiBへ達した現象ではなく、保存済み合計約4GBだけで今回の故障原因とは判断できない。
- 現行ロガーは256MiB前にファイルを分割する。フォーマットで状態が改善しても、容量そのもの・断片化・FAT整合性・媒体等のどれかを比較なしに確定しない。

## 未検証・待ち情報
- カード本体の表記容量、フォーマット時に選んだファイルシステム、現在の挿入先（PC/Spresense/未挿入）をユーザーへ確認中。
- フォーマット後の新規記録試験、SDの再マウント状態、SD上の校正ファイルの有無・必要な復元、容量/断片化が原因かの再現試験は未実施。
- 時刻/距離/姿勢の精度は対象外。

## 出典
- Sony公式Arduino開発ガイド「2.13 SDHCI Library」: https://developer.spresense.sony-semicon.com/development-guides/index?lang=en&page=arduino_developer_guide
- Microsoftファイルシステム仕様比較「Limits」: https://learn.microsoft.com/en-us/windows/win32/fileio/filesystem-functionality-comparison
- ローカルcommon/spresense_binary.hのrotateBytes、先行013のstaging_result.json。

## 証跡
reports/raw/2026-10-27_015_sd_capacity_formatのusb_readonly.txt、status.json、followup_usb.txt。
