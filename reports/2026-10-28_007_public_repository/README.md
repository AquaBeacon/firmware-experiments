# 実験用ファームウェアの公開

## 前提

ユーザーの依頼により、AquaBeacon Organizationへ実験用コードをpublicで公開する。元の作業フォルダーや既存のGitHubリポジトリの実装は変更しない。公開用チェックアウトは隣接する `firmware-experiments`。

## 実施

- 公開先: https://github.com/AquaBeacon/firmware-experiments
- 親子Pico 2 W、Spresense、PCツール、仕様、過去の検証要約をコピー。
- APパスワードはサンプル値へ置換。元のパスワードが公開対象ファイルに残っていないことを確認。
- `reports/raw/`、取得データ `data/`、過去レポートの証拠ファイル、ビルド生成物、ローカル秘密設定を除外。
- GitHubトークン、AWSアクセスキー、OpenAIキー、秘密鍵の一般的な形式を公開対象ファイルで検査し、検出なし。任意形式の秘密を網羅する検査ではない。
- PlatformIOのローカル専用core_dir指定を除去。依存物の再利用のため今回の検証時のみ環境変数で既存core_dirを指定。
- 公開用コードの差分はAPパスワードとWi-Fi試験スクリプトのサンプル値化のみ。include/pins.hは元ファイルとバイト一致。

## 実測・検証

- 公開用コピーで `pio run` 相当の既定ビルドを実施。parent / child100ともSUCCESS。
- ビルド生ログは元作業フォルダーの `reports/raw/github_publication_build.txt` に保存。
- 公開用コピーで `python scripts/test_host.py` を実行し終了コード0。生ログは元作業フォルダーの `reports/raw/github_publication_host.txt` に保存。
- GitHubのリポジトリ設定がPUBLICであることをAPIで確認。公開コードの反映先はmainブランチ。

## 未検証

新たな実機書込み、Spresenseのコンパイル・書込み、機器Webへの接続、時刻・距離・姿勢の実測精度は未検証。PCのWi-Fi切替、SDフォーマット、既存ログ削除は行っていない。
