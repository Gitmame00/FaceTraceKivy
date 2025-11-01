import os
import csv
import datetime
import platform
import socket
import uuid
import glob

class LogManager:
    """
    顔認識ログを日付ごとに自動保存するモジュール。
    フォルダ構造: Record/YYYY/MM/YYYYMMDD_DeviceID.csv
    """

    def __init__(self):
        self.base_dir = "Record"
        os.makedirs(self.base_dir, exist_ok=True)
        self.device_id = self._get_device_id()

    # ---- デバイス情報の取得 ----
    def _get_device_id(self):
        node = platform.node() or socket.gethostname()
        mac = uuid.getnode()
        return f"{node}_{mac % 1000:03d}"

    # ---- ログファイルパスの生成 ----
    def _get_record_path(self):
        now = datetime.datetime.now()
        year = str(now.year)
        month = f"{now.month:02d}"
        day = f"{now.year}{now.month:02d}{now.day:02d}"

        dir_path = os.path.join(self.base_dir, year, month)
        os.makedirs(dir_path, exist_ok=True)

        filename = f"{day}_{self.device_id}.csv"
        return os.path.join(dir_path, filename)

    # ---- 記録を追記 ----
    def log(self, name, event="認識"):
        path = self._get_record_path()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([now, name, event])

        return path

    # ---- ログの閲覧 ----
    def read_latest_log(self):
        """最新の日付のログを取得（末尾数行）"""
        path = self._get_record_path()
        if not os.path.exists(path):
            return "本日のログはまだありません。"
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()[-10:]
        return "".join(lines)

    # ---- ログの削除 ----
    def delete_today_log(self):
        """本日分のログを削除"""
        path = self._get_record_path()
        if os.path.exists(path):
            os.remove(path)
            return f"{os.path.basename(path)} を削除しました。"
        return "削除対象のログがありません。"
    
     # ---- ログの削除 ----
    def delete_today_log(self):
        """本日分のログファイルを削除する"""
        path = self._get_record_path()
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"ログファイル {os.path.basename(path)} を削除しました。")
                return f"本日({os.path.basename(path).split('_')[0]})のログを削除しました。"
            except Exception as e:
                print(f"⚠ ログファイルの削除に失敗しました: {e}")
                return "エラー: ログの削除に失敗しました。"
        return "削除対象のログはありません。"
    

    def read_log_for_date(self, year, month, day):
        """指定された年月日のログファイルを探して、その内容を返す"""
        try:
            # 1. 検索する日付の文字列と、その月のフォルダパスを生成
            date_str = f"{int(year)}{int(month):02d}{int(day):02d}"
            dir_path = os.path.join(self.base_dir, str(year), f"{int(month):02d}")

            # 2. フォルダが存在しない場合は、ログなしとして返す
            if not os.path.isdir(dir_path):
                return f"{year}年{month}月のログフォルダはありません。"

            # 3. globを使い、日付が一致するCSVファイルを検索
            # 例: "Record/2025/11/20251102_*.csv"
            search_pattern = os.path.join(dir_path, f"{date_str}_*.csv")
            log_files = glob.glob(search_pattern)

            # 4. ファイルが見つかったら、その内容をすべて読み込んで返す
            if log_files:
                filepath = log_files[0] # 最初に見つかったファイルを使用
                with open(filepath, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                return f"{year}年{month}月{day}日のログはありません。"
        except Exception as e:
            print(f"⚠ ログの読み込み中にエラーが発生しました: {e}")
            return "エラー: ログの読み込みに失敗しました。"    