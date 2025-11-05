[app]

# (必須) アプリのタイトル
title = FaceTrace

# (必須) パッケージ名（英小文字・数字・アンダースコアのみ）
package.name = facetrace

# (必須) パッケージドメイン（逆ドメイン形式が推奨）
package.domain = org.example

# (必須) ソースコードが含まれるディレクトリ
source.dir = .

# (オプション) 除外するディレクトリ（仮想環境やテスト類）
source.exclude_dirs = tests, .venv, .venv312, venv, venv312

# (オプション) 除外ファイル
source.exclude_patterns = Record/*, config.json, temp_scenes/*

# (必須) 含める拡張子
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,xml,db

# (必須) 特定ファイルをAPKに含める
source.include_patterns = assets/fonts/*.ttf, *.xml, *.db

# (必須) バージョン
version = 0.1

# ✅ 安定構成（最重要）
requirements = python3==3.8.10, kivy==2.1.0, opencv-python==4.5.5.64, numpy==1.21.6, pillow==9.5.0, plyer==2.1.0

# (オプション) アプリの向き
orientation = portrait

# (オプション) フルスクリーン設定
fullscreen = 0

# (Android) API・NDK設定（この組み合わせが安定）
android.api = 31
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.archs = armeabi-v7a,arm64-v8a

# (Android) 必要な権限
android.permissions = CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# (Android) スプラッシュスクリーン背景色
android.presplash_color = #000000

# (Android) Kivyビルド用ブランチ（安定）
p4a.branch = master

# (Android) 不要ファイルを除外してビルドエラー回避
requirements.source.exclude_exts = pyc,pyo,a,pyx,pxd,so

# (Android) 最適化のための追加環境設定
extra_env_files = false


[buildozer]

# (必須) ログレベル（詳細）
log_level = 2

# (オプション) ルート実行時の警告を無視
warn_on_root = 0

# (オプション) ローカルビルドキャッシュを維持
# （再ビルド時に依存関係を再利用）
use_cache = 1

# (オプション) ビルドディレクトリ
build_dir = ./.buildozer/build

# (オプション) 出力APKの保存先
bin_dir = ./bin

# (オプション) ビルドが途中で落ちてもログを保存
log_filename = buildozer.log

# (推奨) Android SDK / NDK が存在する場合はパス指定可能
# android.sdk_path = /opt/android-sdk
# android.ndk_path = /opt/android-ndk
