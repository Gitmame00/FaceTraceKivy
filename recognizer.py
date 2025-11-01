import cv2
import numpy as np

class Recognizer:
    def __init__(self):
        # Haar Cascade分類器の読み込みは変更なし
        self.face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
        # LBPH認識器を初期化
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        # モデルが学習済みかどうかを管理するフラグ
        self.is_trained = False
        # IDと名前を対応させる辞書
        self.names = {}

    def train_from_db(self, db_manager):
        """データベースから顔画像とラベルを取得してモデルを学習する"""
        print("[INFO] データベースから学習を開始します...")
        
        # DBから学習用の顔画像(faces)、ラベル(labels)、名前辞書(names)を取得
        faces, labels, names = db_manager.get_all_faces_for_training()

        if not faces or len(labels) == 0:
            print("[警告] データベースに学習データがありません。")
            self.is_trained = False
            return

        # 取得したデータでモデルを学習
        self.recognizer.train(faces, labels)
        self.names = names  # IDと名前の辞書を保存
        self.is_trained = True
        print(f"[INFO] {len(np.unique(labels))} 人の顔の学習が完了しました。")

    def detect_faces(self, bgr_frame):
        """顔検出機能は変更なし"""
        gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        return faces

    def recognize(self, face_img):
        """顔認証機能。名前も一緒に返すように変更"""
        if not self.is_trained:
            return -1, 0, "N/A" # ID, 確信度, 名前の3つを返す

        label, confidence = self.recognizer.predict(face_img)
        
        # self.names辞書からIDに対応する名前を取得
        name = self.names.get(label, "不明な人物")
        
        return label, confidence, name