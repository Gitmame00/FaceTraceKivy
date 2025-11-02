[app]

# (必須) アプリのタイトル
title = FaceTrace

# (必須) パッケージ名。アルファベット小文字のみ使用
package.name = facetrace

# (必須) パッケージドメイン。通常は逆ドメイン形式
package.domain = org.example

# (必須) ソースコードが含まれるディレクトリ
source.dir = .

# (オプション) ソースコードから除外するディレクトリ (カンマ区切り)
source.exclude_dirs = tests, .venv, .venv312, venv, venv312

# (オプション) ソースコードから除外するファイル (ワイルドカード使用可)
source.exclude_patterns = Record/*, config.json, temp_scenes/*

# (必須) APKに含めるファイルの拡張子
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,xml,db

# (オプション) APKに含める特定のファイルやフォルダのパターン
# これにより、haarcascade_frontalface_default.xml とフォントファイルが確実に含まれる
source.include_patterns = assets/fonts/*.ttf, *.xml, *.db

# (必須) 起動時に実行されるスクリプトのバージョン
version = 0.1

# (必須) アプリが依存するPythonライブラリの一覧 (カンマ区切り)
# ★★★ あなたの指定に基づき、バージョンを固定 ★★★
requirements = python3==3.8.10,kivy==2.1.0,opencv,numpy==1.21.6,pillow==9.5.0,plyer==2.1.0

# (オプション) アプリの向き (landscape, portrait, all)
orientation = portrait

# (オプション) アプリのアイコンとして使用する画像のパス
#icon.filename = %(source.dir)s/icon.png

# (オプション) スプラッシュスクリーン (起動画面) として使用する画像のパス
#presplash.filename = %(source.dir)s/presplash.png

# (オプション) WebViewを使用する場合のローディング画像
# presplash.filename = %(source.dir)s/data/images/loader.gif

# (オプション) アプリがフルスクリーンモードで実行されるかどうか
fullscreen = 0

# (Android) Android特有の設定
android.api = 30
android.minapi = 21
android.sdk = 24
android.ndk = 25b
android.archs = armeabi-v7a,arm64-v8a

# (Android) アプリが必要とする権限 (カンマ区切り)
# カメラ、外部ストレージの読み書き権限を要求
android.permissions = CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# (Android) スプラッシュスクリーンが表示されている間にKivyを初期化するかどうか
android.presplash_color = #000000

# (Android) スプラッシュスクリーンをアニメーション化する場合
# android.presplash_animated_icon = %(presplash.filename)s

# (Android) ビルドに使用するpython-for-androidのブランチ (安定のためmasterを推奨)
p4a.branch = master


[buildozer]

# (必須) ログレベル (2 = デバッグ情報)
log_level = 2

# (オプション) 警告時にビルドを停止するかどうか
warn_on_root = 0

# (オプション) ビルドディレクトリ
# build_dir = ./.buildozer/build

# (オプション) binディレクトリ
# bin_dir = ./bin