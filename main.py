import os
import cv2
import numpy as np
import platform
import threading
import shutil ### ★ 変更点 ★ ### フォルダごと削除するためにshutilをインポート
import json # ★★★ ポップアップで使うのでインポート
import datetime 
from recorder_controller import RecorderController
from kivy.factory import Factory
from kivy.properties import StringProperty
from kivy.clock import mainthread
from PIL import Image as PilImage
from PIL import ImageDraw, ImageFont
from plyer import filechooser
from kivy.lang import Builder
from kivy.app import App
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image as KivyImage
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.core.text import LabelBase
from kivy.resources import resource_add_path
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.properties import BooleanProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior

from log_manager import LogManager
from recorder_controller import RecorderController
from db_manager import DBManager
from recognizer import Recognizer

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, 'FaceBase.db')
TEMP_DIR = os.path.join(APP_DIR, 'temp_scenes')
os.makedirs(TEMP_DIR, exist_ok=True)

FONT_NAME = 'sans'
try:
    font_path = os.path.join(os.path.dirname(__file__), 'assets/fonts/')
    resource_add_path(font_path)
    LabelBase.register('NotoJP', 'NotoSansJP-Regular.ttf')
    FONT_NAME = 'NotoJP'
except Exception as e:
    print(f"フォントの読み込みに失敗しました: {e}")

class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    '''Adds selection and focus behaviour to the view.'''
    
class SelectableLabel(RecycleDataViewBehavior, Label):
    '''Add selection support to the Label'''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        '''Catch and handle the view changes'''
        self.index = index
        self.text = data.get('text', '') 
        return super(SelectableLabel, self).refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        '''Add selection on touch down'''
        if super(SelectableLabel, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        '''Respond to the selection of items in the view.'''
        self.selected = is_selected
        
        if not (0 <= index < len(rv.data)):
            return

        if is_selected:
            print("Selection changed to: {0}".format(rv.data[index]))
            
            app = App.get_running_app()
            if app and hasattr(app, 'root') and app.root.has_screen('manage'):
                app.root.get_screen('manage').selected_name = rv.data[index]['text']
        else:
            app = App.get_running_app()
            if app and hasattr(app, 'root') and app.root.has_screen('manage'):
                if app.root.get_screen('manage').selected_name == rv.data[index]['text']:
                    app.root.get_screen('manage').selected_name = ""

class KivyCamera(KivyImage):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.capture = None
        self.frame = None
        self.recognizer = Recognizer()
        self.db_manager = None
        self.pil_font = None
        self.update_event = None

        try:
            self.db_manager = DBManager(DB_PATH)
            print("データベースに正常に接続しました。")
            font_path = os.path.join(APP_DIR, 'assets', 'fonts', 'NotoSansJP-Regular.ttf')
            self.pil_font = ImageFont.truetype(font_path, 24)
        except Exception as e:
            print(f"[初期化エラー] {e}")
            self.pil_font = ImageFont.load_default()

        self.retrain_recognizer()
        
    def start(self, camera_index):
        if self.capture is not None:
            print("カメラは既に起動しています。")
            return True

        print(f"{camera_index}番のカメラを開始します...")
        if platform.system() == "Windows":
            self.capture = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        else:
            self.capture = cv2.VideoCapture(camera_index)
        
        if not self.capture or not self.capture.isOpened():
            print(f"エラー: {camera_index}番のカメラを開けませんでした。")
            self.capture = None
            return False
        
        self.update_event = Clock.schedule_interval(self.update, 1.0 / 30.0)
        print("カメラを開始しました。")
        return True

    def stop(self):
        print("カメラを停止します。")
        if self.update_event:
            self.update_event.cancel()
            self.update_event = None
            
        if self.capture:
            self.capture.release()
            self.capture = None
        
        self.texture = None

    def retrain_recognizer(self):
        if not self.db_manager: return
        self.recognizer = Recognizer()
        self.recognizer.train_from_db(self.db_manager)
        app = App.get_running_app()
        if app and hasattr(app, 'root') and app.root:
            main_screen = app.root.get_screen('main')
            if main_screen:
                result_label = main_screen.ids.get('result_label')
                if result_label:
                    result_label.text = "学習完了！" if self.recognizer.is_trained else "学習データがありません"


    def update(self, dt):
        if not self.capture: return
        ret, self.frame = self.capture.read()
        if not ret: return
        
        display_frame = self.frame.copy()
        app = App.get_running_app()
        if app.is_capturing:
            self.texture = self.frame_to_texture(display_frame)
            return

        result_text = ""
        
        pil_image = PilImage.fromarray(cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)

        faces = self.recognizer.detect_faces(display_frame)

        if self.recognizer.is_trained:
            if len(faces) > 0:
                gray = cv2.cvtColor(display_frame, cv2.COLOR_BGR2GRAY)
                for (x, y, w, h) in faces:
                    if w > 0 and h > 0:
                        face_img = gray[y:y+h, x:x+w]
                        label, confidence, name = self.recognizer.recognize(face_img)
                        
                        # --- ▼▼▼ ここからが変更・追加部分 ▼▼▼ ---
                        
                        is_registered = False  # 登録者かどうかを判定するフラグ
                        
                        if confidence < 100:
                            # 既存の人物と認識した場合
                            result_text = f"{name} ({round(100 - confidence)}%)"
                            outline_color = (0, 255, 0) # 緑
                            is_registered = True
                        else:
                            # 不明な人物の場合
                            result_text = "予測: 不明な人物"
                            outline_color = (255, 255, 0) # 黄
                            name = "Unknown"  # ログ記録用に名前を 'Unknown' とする
                            is_registered = False

                        # RecorderControllerに、認識結果を渡して記録判断を依頼する
                        app.recorder.record(name, is_registered)
                        
                        # --- ▲▲▲ ここまでが変更・追加部分 ▲▲▲ ---

                        draw.rectangle([(x, y), (x+w, y+h)], outline=outline_color, width=2)
                        text_y = max(y - 30, 0)
                        draw.text((x, text_y), result_text, font=self.pil_font, fill=outline_color)
            else:
                result_text = "顔が検出されませんでした"
        else:
            # 学習データがない場合の処理 (ここは変更なし)
            result_text = "学習データがありません。新規登録してください。"
            if len(faces) > 0:
                for (x, y, w, h) in faces:
                    outline_color = (255, 255, 0)
                    draw.rectangle([(x, y), (x+w, y+h)], outline=outline_color, width=2)
                    
                    text_y = max(y - 30, 0)
                    draw.text((x, text_y), "Unknown", font=self.pil_font, fill=outline_color)
            
        display_frame = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        main_screen = app.root.get_screen('main')
        if main_screen:
            result_label = main_screen.ids.get('result_label')
            if result_label: result_label.text = result_text

        self.texture = self.frame_to_texture(display_frame)

    def frame_to_texture(self, frame):
        buf = cv2.flip(frame, 0).tobytes()
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        return texture

    def on_stop(self):
        self.stop()

class RegistrationPopup(Popup):
    def __init__(self, register_callback, **kwargs):
        super().__init__(**kwargs)
        self.register_callback = register_callback
    def submit(self, name):
        if not name or not name.strip(): return
        self.register_callback(name.strip())
        self.dismiss()

class DuplicateConfirmPopup(Popup):
    def __init__(self, confirm_callback, **kwargs):
        super().__init__(**kwargs)
        self.confirm_callback = confirm_callback

    def set_message(self, new_name, existing_name, confidence):
        message = (
            f"入力された名前: '{new_name}'\n\n"
            f"DBの人物: '{existing_name}' (確信度: {confidence}%)\n\n"
            "この2名は、同一人物ですか？"
        )
        self.ids.confirm_text_label.text = message

    def submit(self, is_same_person):
        self.confirm_callback(is_same_person)
        self.dismiss()

class MainScreen(Screen): pass

class ProgressPopup(Popup):
    pass

class ManageScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_name = ""
        self.db = None
        self.search_thread = None
        self.stop_search_thread = False
        self.progress_popup = None

    def on_enter(self):
        print("管理画面に入りました。DBに接続し、リストを更新します。")
        try:
            self.db = DBManager('FaceBase.db')
            self.populate_list()
            self.db = DBManager(DB_PATH)

        except Exception as e:
            print(f"[エラー] 管理画面でのDB接続に失敗しました: {e}")
            self.db = None

    def on_leave(self):
        print("管理画面を離れます。DB接続を閉じます。")
        if self.db:
            self.db.close()
            self.db = None

    def populate_list(self):
        if not self.db:
            print("[警告] populate_list: DBに接続されていません。")
            return
            
        names = self.db.get_all_names()
        self.ids.user_list_rv.data = [{'text': name} for name in names]
        self.selected_name = ""
        self.ids.user_list_rv.layout_manager.clear_selection()

    def delete_selected(self):
        if not self.selected_name:
            popup = Popup(title='警告', content=Label(text='削除する名前を選択してください', font_name=FONT_NAME), size_hint=(0.8, 0.3))
            popup.open()
            return
            
        selected_name = self.selected_name
        
        confirm_popup = Popup(title='', separator_height=0, size_hint=(0.8, 0.4))
        content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
        message = Label(text=f"本当に「{selected_name}」を削除しますか？", font_name=FONT_NAME)
        btn_box = BoxLayout(size_hint_y=None, height='50dp', spacing='10dp')
        
        def confirm_delete_action(instance):
            confirm_popup.dismiss()
            self._execute_delete(selected_name)
        
        ok_button = Button(text="はい, 削除します", font_name=FONT_NAME, on_press=confirm_delete_action)
        cancel_button = Button(text="キャンセル", font_name=FONT_NAME, on_press=confirm_popup.dismiss)
        
        btn_box.add_widget(ok_button)
        btn_box.add_widget(cancel_button)
        content.add_widget(message)
        content.add_widget(btn_box)
        confirm_popup.content = content
        confirm_popup.open()

    def _execute_delete(self, name_to_delete):
        db = DBManager(DB_PATH)
        if not self.db:
            print("[警告] _execute_delete: DBに接続されていません。")
            return

        print(f"「{name_to_delete}」を削除します...")
        
        self.db.delete_person_by_name(name_to_delete)
        
        print("削除が完了しました。")
        self.populate_list()
        
        app = App.get_running_app()
        main_screen = app.root.get_screen('main')
        camera_widget = main_screen.ids.camera_display
        result_label = main_screen.ids.result_label
        result_label.text = f"「{name_to_delete}」を削除しました。\n再学習が必要です..."
        
        Clock.schedule_once(lambda dt: camera_widget.retrain_recognizer(), 0.5)
        
        popup = Popup(title='', 
                      separator_height=0,
                      content=Label(text=f"「{name_to_delete}」を削除しました。", font_name=FONT_NAME),
                      size_hint=(0.8, 0.3))
        popup.open()

    ### ★ 変更点 ★ ###
    # 一時フォルダをクリーンアップするメソッドを新設
    def _clear_temp_scenes(self):
        """temp_scenesフォルダの中身を空にする"""
        if os.path.exists(TEMP_DIR):
            try:
                # フォルダごと中身をすべて削除
                shutil.rmtree(TEMP_DIR)
                print(f"一時フォルダ {TEMP_DIR} をクリーンアップしました。")
            except Exception as e:
                print(f"[エラー] 一時フォルダのクリーンアップに失敗しました: {e}")
        
        # フォルダを再度作成
        os.makedirs(TEMP_DIR, exist_ok=True)


    def open_file_chooser(self):
        if not self.selected_name:
            popup = Popup(title='警告',
                          content=Label(text='検索する名前をリストから選択してください', font_name=FONT_NAME),
                          size_hint=(0.8, 0.3))
            popup.open()
            return

        print(f"「{self.selected_name}」さんを検索するための動画ファイルを選択します...")
        
        filechooser.open_file(
            on_selection=self.start_video_search,
            title="検索対象の動画ファイルを選択",
            filters=[
                ("MP4 Video", "*.mp4"),
                ("AVI Video", "*.avi"),
                ("MOV Video", "*.mov"),
                ("All files", "*.*")
            ]
        )

    def start_video_search(self, selection):
        if not selection:
            print("動画ファイルが選択されませんでした。")
            return
        
        ### ★ 変更点 ★ ###
        # 新しい検索を開始する前に、まず一時ファイルを削除する
        self._clear_temp_scenes()
        
        filepath = selection[0]
        target_name = self.selected_name
        
        print(f"動画解析を開始します: {filepath}")
        print(f"検索対象: {target_name}")

        progress_popup_kv = '''
ProgressPopup:
    size_hint: 0.8, 0.3
    auto_dismiss: False
    title: ''
    separator_height: 0
    Label:
        id: progress_label
        text: "動画を解析中です..."
        font_name: app.font_name
'''
        self.progress_popup = Builder.load_string(progress_popup_kv)
        
        self.progress_popup.open()
        
        self.stop_search_thread = False

        self.search_thread = threading.Thread(
            target=self._video_search_thread_target,
            args=(filepath, target_name)
        )
        self.search_thread.daemon = True
        self.search_thread.start()

    def _video_search_thread_target(self, filepath, target_name):
        """バックグラウンドスレッドで実行される、重い動画解析処理"""
        
        target_label = None
        db_for_thread = None
        try:
            db_for_thread = DBManager(DB_PATH)
            target_label = db_for_thread.get_label_by_name(target_name)
        except Exception as e:
            print(f"[スレッドエラー] DB処理中にエラーが発生しました: {e}")
            # ★ 変更点 ★
            Clock.schedule_once(lambda dt: self.on_search_complete([], error_message="DBエラーが発生しました。"))
            return
        finally:
            if db_for_thread:
                db_for_thread.close()

        if target_label is None:
            print(f"エラー: DBで'{target_name}'のIDが見つかりません。")
            # ★ 変更点 ★
            Clock.schedule_once(lambda dt: self.on_search_complete([], error_message=f"'{target_name}'はDBに未登録です。"))
            return

        # メイン画面のRecognizerを取得
        app = App.get_running_app()
        camera_widget = app.root.get_screen('main').ids.camera_display
        recognizer = camera_widget.recognizer
        
        cap = cv2.VideoCapture(filepath)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        found_scenes = []
        frame_count = 0
        
        while True:
            if self.stop_search_thread:
                print("動画解析が中断されました。")
                break

            ret, frame = cap.read()
            if not ret: break
            frame_count += 1

            if frame_count % 50 == 0 and total_frames > 0:
                progress = (frame_count / total_frames) * 100
                self.update_progress(f"解析中... {progress:.0f}%")

            if frame is None or frame.size == 0:
                continue
            
            if frame_count % 10 != 0: continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = recognizer.detect_faces(frame)
            
            for (x, y, w, h) in faces:
                if w > 0 and h > 0:
                    face_img = gray[y:y+h, x:x+w]
                    label, confidence, name = recognizer.recognize(face_img)
                    
                    if label == target_label and confidence < 80:
                        timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
                        if not found_scenes or timestamp - found_scenes[-1]['timestamp'] > 3.0:
                            thumbnail_path = os.path.join(TEMP_DIR, f"scene_{len(found_scenes)}.jpg")
                            cv2.imwrite(thumbnail_path, frame)
                            found_scenes.append({'image_source': thumbnail_path, 'timestamp': timestamp})
                        break
        
        cap.release()
        
        # ★ 変更点 ★
        Clock.schedule_once(lambda dt: self.on_search_complete(found_scenes))



    def update_progress(self, message):
        if self.progress_popup:
            self.progress_popup.ids.progress_label.text = message

    def on_search_complete(self, scenes, error_message=None):
        """解析完了後、メインスレッドで実行されるUI更新処理"""

        # 1. プログレスポップアップを、まず閉じる
        if self.progress_popup:
            self.progress_popup.dismiss()
            self.progress_popup = None
        
        # 2. もし、エラーメッセージが渡されていたら...
        if error_message:
            print(f"動画解析中にエラーが発生しました: {error_message}")
            # エラー内容をポップアップでユーザーに通知
            popup = Popup(title='エラー',
                          content=Label(text=error_message, font_name=FONT_NAME),
                          size_hint=(0.8, 0.3))
            popup.open()
            return # ここで処理を中断

        print(f"動画解析が完了しました。{len(scenes)}件見つかりました。")

        app = App.get_running_app()
        result_screen = app.root.get_screen('search_result')
        
        result_screen.ids.result_title_label.text = f"「{self.selected_name}」の検索結果 ({len(scenes)}件)"
        
        rv_data = []
        for scene in scenes:
            minutes, seconds = divmod(scene['timestamp'], 60)
            info_text = f"時間: {int(minutes):02d}分 {int(seconds):02d}秒"
            rv_data.append({
                'image_source': scene['image_source'],
                'info_text': info_text
            })
            
        result_screen.ids.scene_list_rv.data = rv_data
        
        app.root.current = 'search_result'

class SearchResultScreen(Screen):
    pass

class LogScreen(Screen):
    pass

class SceneItem(BoxLayout):
    image_source = StringProperty('')
    info_text = StringProperty('')


class FaceTraceApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_name = FONT_NAME
        self.is_capturing = False
        self.capture_name = ""
        self.capture_count = 0
        self.capture_limit = 10
        self.captured_images = []
        self.is_checking_duplicate = False

        # --- 新しいコントローラーとマネージャーのインスタンスを作成 ---
        self.recorder = RecorderController()
        self.log_manager = LogManager()

    def build(self):
        # .kvファイルが自動で読み込まれるので、このままでOK
        pass

    def toggle_recording(self):
        """記録開始／停止の切替"""
        is_recording = self.recorder.toggle_recording()
        record_button = self.root.get_screen('main').ids.record_button
        record_button.text = "記録停止" if is_recording else "記録開始"

    def open_record_setting(self):
        """再記録設定のポップアップを開く (インデント修正済)"""
        
        # 1. ポップアップの中身を準備
        layout = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')

        layout.add_widget(Label(text="登録者の再記録間隔（分）:", font_name=self.font_name))
        registered_input = TextInput(
            text=str(self.recorder.registered_interval), multiline=False, input_filter='int'
        )
        layout.add_widget(registered_input)

        layout.add_widget(Label(text="未登録者の再記録間隔（分）:", font_name=self.font_name))
        unregistered_input = TextInput(
            text=str(self.recorder.unregistered_interval), multiline=False, input_filter='int'
        )
        layout.add_widget(unregistered_input)

        btn_box = BoxLayout(size_hint_y=None, height='50dp', spacing='10dp')
        save_button = Button(text="保存", font_name=self.font_name)
        cancel_button = Button(text="キャンセル", font_name=self.font_name)
        btn_box.add_widget(save_button)
        btn_box.add_widget(cancel_button)
        layout.add_widget(btn_box)
        
        popup = Popup(title="再記録間隔設定", content=layout, size_hint=(0.8, 0.5))

        # 2. 「保存」ボタンの動作を定義
        def save_action(instance):
            try:
                reg_interval = int(registered_input.text)
                unreg_interval = int(unregistered_input.text)
                
                self.recorder.registered_interval = reg_interval
                self.recorder.unregistered_interval = unreg_interval
                
                if self.recorder.save_config():
                    popup.dismiss()
                else:
                    error_popup = Popup(title='エラー', content=Label(text='設定の保存に失敗しました。'), size_hint=(0.6, 0.3))
                    error_popup.open()

            except ValueError:
                error_popup = Popup(title='エラー', content=Label(text='数値を入力してください。'), size_hint=(0.6, 0.3))
                error_popup.open()

        # 3. ボタンと動作を結びつける
        save_button.bind(on_press=save_action)
        cancel_button.bind(on_press=popup.dismiss)
        
        # 4. ポップアップを表示
        popup.open()

    def show_logs(self):
        """ログスクリーンを開き、スピナーに今日の日付をセットして、本日のログを表示する"""
        log_screen = self.root.get_screen('log_screen')
        
        # --- スピナーに選択肢とデフォルト値(今日)を設定 ---
        now = datetime.datetime.now()
        
        # 年スピナー: 5年前から今年まで
        year_spinner = log_screen.ids.year_spinner
        year_spinner.values = [str(y) for y in range(now.year - 5, now.year + 1)]
        year_spinner.text = str(now.year)
        
        # 月スピナー: 1月から12月
        month_spinner = log_screen.ids.month_spinner
        month_spinner.values = [f"{m:02d}" for m in range(1, 13)]
        month_spinner.text = f"{now.month:02d}"

        # 日スピナー: 1日から31日
        day_spinner = log_screen.ids.day_spinner
        day_spinner.values = [f"{d:02d}" for d in range(1, 32)]
        day_spinner.text = f"{now.day:02d}"

        # --- 画面を開くと同時に、本日のログを読み込む ---
        self.view_log_by_date()

        # --- ログスクリーンに移動 ---
        self.root.current = 'log_screen'

    ### ★★★ このメソッドを丸ごと新設 ★★★ ###
    def view_log_by_date(self):
        """スピナーで選択された日付のログを読み込んで表示する"""
        log_screen = self.root.get_screen('log_screen')
        
        # スピナーから選択された値を取得
        year = log_screen.ids.year_spinner.text
        month = log_screen.ids.month_spinner.text
        day = log_screen.ids.day_spinner.text
        
        if year == "年" or month == "月" or day == "日":
            log_screen.ids.log_display.text = "年・月・日をすべて選択してください。"
            return
            
        # log_managerに、指定した日付のログを問い合わせる
        log_text = self.log_manager.read_log_for_date(year, month, day)
        
        # 結果をTextInputに表示
        log_screen.ids.log_display.text = log_text


    def open_registration_popup(self):
        if self.is_capturing: return
        popup = RegistrationPopup(register_callback=self.start_face_capture)
        popup.open()

    def toggle_camera(self):
        main_screen = self.root.get_screen('main')
        camera_widget = main_screen.ids.camera_display
        button = main_screen.ids.toggle_camera_button
        spinner = main_screen.ids.camera_spinner
        result_label = main_screen.ids.result_label

        if camera_widget.capture is None:
            camera_index = int(spinner.text)
            
            if camera_widget.start(camera_index):
                button.text = "カメラ停止"
                spinner.disabled = True
                result_label.text = "カメラに顔を映してください"                
            else:
                main_screen.ids.result_label.text = f"{camera_index}番のカメラを開けませんでした"
        else:
            camera_widget.stop()
            button.text = "カメラ開始"
            spinner.disabled = False
            result_label.text = "カメラは停止しています"

    def start_face_capture(self, name):
        print(f"「{name}」さんの登録プロセスを開始します。まず重複チェックを行います...")
        
        self.capture_name = name
        self.is_checking_duplicate = True
        
        main_screen = self.root.get_screen('main')
        result_label = main_screen.ids.result_label
        result_label.text = "重複チェック中... 正面を向いてください"
        
        Clock.schedule_interval(self.check_duplicate_step, 0.5)

    def check_duplicate_step(self, dt):
        if not self.is_checking_duplicate:
            return False

        main_screen = self.root.get_screen('main')
        camera_widget = main_screen.ids.camera_display
        result_label = main_screen.ids.result_label

        if camera_widget.frame is None:
            return

        if not camera_widget.recognizer.is_trained:
            print("学習済みモデルがないため、重複チェックをスキップします。")
            self.is_checking_duplicate = False
            self.proceed_to_capture()
            return False

        frame = camera_widget.frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = camera_widget.recognizer.detect_faces(frame)

        if len(faces) == 1:
            print("重複チェック用の顔を検出しました。認証を試みます...")
            
            x, y, w, h = faces[0]
            face_img = gray[y:y+h, x:x+w]
            
            if face_img.size == 0: return

            label, confidence, name = camera_widget.recognizer.recognize(face_img)
            
            confidence_percent = round(100 - confidence)
            
            if confidence < 40:
                print(f"[警告] 重複の可能性があります！")
                
                self.is_checking_duplicate = False
                Clock.unschedule(self.check_duplicate_step)

                popup = DuplicateConfirmPopup(
                    confirm_callback=lambda is_same: self.handle_duplicate_confirm(is_same, existing_name=name)
                )
            
                popup.set_message(self.capture_name, name, confidence_percent)
                popup.open()
                return False
            else:
                print("重複は見つかりませんでした。新規登録に進みます。")
                self.is_checking_duplicate = False
                self.proceed_to_capture()
                return False
                 
        elif len(faces) > 1:
            result_label.text = "重複チェック中... 顔が複数検出されました"
        else:
            result_label.text = "重複チェック中... 顔を検出できません"

    def handle_duplicate_confirm(self, is_same_person, existing_name):
        if is_same_person:
            print(f"ユーザーが同一人物と判断しました。'{existing_name}'のデータとして顔を10枚撮影します。")
            self.capture_name = existing_name
            self.proceed_to_capture()
        else:
            print("ユーザーが別人であると判断しました。新規登録を続行します。")
            self.proceed_to_capture() 

    def proceed_to_capture(self):
        print(f"「{self.capture_name}」さんの顔を{self.capture_limit}枚撮影します。")
        
        self.is_capturing = True
        self.capture_count = 0
        self.captured_images = []
        
        Clock.schedule_interval(self.capture_step, 0.2)

    def capture_step(self, dt):
        main_screen = self.root.get_screen('main')
        camera_widget = main_screen.ids.camera_display
        result_label = main_screen.ids.result_label
        if camera_widget.frame is None: return

        frame = camera_widget.frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))

        feedback_text = ""
        if len(faces) == 1:
            x, y, w, h = faces[0]
            if w > 0 and h > 0: # ★★★ ここのコロン(:)を修正しました ★★★
                face_img = gray[y:y+h, x:x+w]
                self.captured_images.append(face_img)
                self.capture_count += 1
                feedback_text = f"撮影成功！ ({self.capture_count}/{self.capture_limit})"
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        elif len(faces) > 1: feedback_text = "顔が複数検出されました"
        else: feedback_text = "顔を検出できません"

        result_label.text = f"{self.capture_limit}枚撮影します。\n{feedback_text}"
        camera_widget.texture = camera_widget.frame_to_texture(frame)
        if self.capture_count >= self.capture_limit:
            self.finish_capture()
            return False

    def finish_capture(self):
        Clock.unschedule(self.capture_step)
        print(f"{self.capture_count}枚の撮影が完了しました。データベースに保存します。")
        self.is_capturing = False
    
        main_screen = self.root.get_screen('main')
        camera_widget = main_screen.ids.camera_display
        result_label = main_screen.ids.result_label
    
        db = DBManager(DB_PATH)

        existing_names = db.get_all_names()
        if self.capture_name in existing_names:
            for img in self.captured_images:
                db.add_face_to_existing_person(self.capture_name, img)
            result_label.text = f"「{self.capture_name}」さんにデータを追加しました。"
        else:
            for img in self.captured_images:
                db.add_face(self.capture_name, img)
            result_label.text = f"「{self.capture_name}」さんを新規登録しました！"
    
        result_label.text += "\n新しい顔を学習中です...お待ちください。"
        Clock.schedule_once(lambda dt: camera_widget.retrain_recognizer(), 0.1)

    def on_stop(self):
        if self.root:
            main_screen = self.root.get_screen('main')
            if main_screen and main_screen.ids:
                camera_widget = main_screen.ids.get('camera_display')
                if camera_widget:
                    camera_widget.on_stop()
            
            manage_screen = self.root.get_screen('manage')
            if hasattr(manage_screen, 'stop_search_thread'):
                manage_screen.stop_search_thread = True
            
            # アプリ終了時に一時ファイルをクリーンアップ (動画検索機能の名残)
            if hasattr(manage_screen, '_clear_temp_scenes'):
                manage_screen._clear_temp_scenes()


    def delete_log(self):
        """ログ削除の確認ポップアップを表示する"""
        
        content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
        message = Label(text="本当に本日分のログをすべて削除しますか？\nこの操作は元に戻せません。", font_name=self.font_name)
        content.add_widget(message)

        btn_box = BoxLayout(size_hint_y=None, height='50dp', spacing='10dp')
        
        confirm_popup = Popup(title='ログの削除確認', content=content, size_hint=(0.8, 0.4))
        
        # --- 「はい、削除します」ボタンが押されたときの動作を定義 ---
        def _execute_delete(instance):
            confirm_popup.dismiss() # 確認ポップアップを閉じる
            
            # log_managerに削除を依頼
            result_message = self.log_manager.delete_today_log()
            
            # 実行結果をユーザーに通知
            result_popup = Popup(title='削除結果', 
                                 content=Label(text=result_message, font_name=self.font_name), 
                                 size_hint=(0.7, 0.3))
            result_popup.open()
            
            # ★★★ ログ表示をリフレッシュする ★★★
            self.show_logs()

        ok_button = Button(text="はい, 削除します", font_name=self.font_name)
        ok_button.bind(on_press=_execute_delete)
        
        cancel_button = Button(text="キャンセル", font_name=self.font_name)
        cancel_button.bind(on_press=confirm_popup.dismiss)

        btn_box.add_widget(ok_button)
        btn_box.add_widget(cancel_button)
        content.add_widget(btn_box)

        confirm_popup.open()          

if __name__ == '__main__':
    FaceTraceApp().run()