import os
import json
import datetime
from log_manager import LogManager

class RecorderController:
    """
    顔認識イベントに基づき、再記録間隔を考慮してログ記録を制御する。
    """
    def __init__(self, config_file="config.json"):
        self.log_manager = LogManager()
        self.config_file = config_file
        self.last_recorded_times = {}  # { 'name': datetime_object }
        self.is_recording = False

        # --- 設定の読み込み ---
        self.registered_interval = 10  # 登録者の再記録間隔（分）
        self.unregistered_interval = 1 # 未登録者の再記録間隔（分）
        self.load_config()

    def load_config(self):
        """設定ファイルから再記録間隔を読み込む"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.registered_interval = config.get("registered_interval", self.registered_interval)
                    self.unregistered_interval = config.get("unregistered_interval", self.unregistered_interval)
                print("設定を読み込みました。")
            except Exception as e:
                print(f"⚠ 設定ファイルの読み込みに失敗しました: {e}")
        else:
            print("設定ファイルが見つからないため、デフォルト値を使用します。")

    def save_config(self):
        """現在の設定をファイルに保存する"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                config = {
                    "registered_interval": self.registered_interval,
                    "unregistered_interval": self.unregistered_interval
                }
                json.dump(config, f, ensure_ascii=False, indent=2)
            print("設定を保存しました。")
            return True
        except Exception as e:
            print(f"⚠ 設定の保存に失敗しました: {e}")
            return False

    def toggle_recording(self):
        """記録モードのON/OFFを切り替える"""
        self.is_recording = not self.is_recording
        print(f"記録モード: {'ON' if self.is_recording else 'OFF'}")
        return self.is_recording

    def record(self, name, is_registered):
        """
        記録条件を判断し、LogManagerに記録を依頼する。
        - is_recordingがTrueでなければ何もしない。
        - 前回の記録から指定されたインターバルが経過していなければ記録しない。
        """
        if not self.is_recording:
            return

        now = datetime.datetime.now()
        last_time = self.last_recorded_times.get(name)

        interval_minutes = self.registered_interval if is_registered else self.unregistered_interval
        
        # ログに記録すべきか判断
        should_record = False
        if last_time is None:
            # 初めて認識した人物は記録
            should_record = True
        else:
            # 前回の記録からの経過時間（分）
            elapsed_minutes = (now - last_time).total_seconds() / 60
            if elapsed_minutes >= interval_minutes:
                should_record = True

        if should_record:
            event = "登録者" if is_registered else "未登録者"
            self.log_manager.log(name, event)
            self.last_recorded_times[name] = now # 最終記録時刻を更新
            print(f"✅ ログに記録: {name} ({event})")