import sqlite3
import cv2
import numpy as np

class DBManager:
    def __init__(self, db_path='faces.db'):
        sqlite3.register_adapter(np.ndarray, self._adapt_array)
        sqlite3.register_converter("image", self._convert_array)
        
        self.conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        self._ensure_tables()

    def _adapt_array(self, arr):
        success, encoded_image = cv2.imencode('.jpg', arr)
        return encoded_image.tobytes() if success else None

    def _convert_array(self, text):
        nparr = np.frombuffer(text, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

    def _ensure_tables(self):
        c = self.conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                face_image image NOT NULL
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS names (
                label INTEGER PRIMARY KEY,
                name TEXT UNIQUE
            )
        ''')
        self.conn.commit()

    def add_face(self, name, face_image):
        c = self.conn.cursor()
        c.execute('INSERT OR IGNORE INTO names (name) VALUES (?)', (name,))
        self.conn.commit()
        
        c.execute('INSERT INTO faces (name, face_image) VALUES (?, ?)', (name, face_image))
        self.conn.commit()

    def add_face_to_existing_person(self, name, face_image):
        """既存の人物名に、新しい顔画像を追加する"""
        c = self.conn.cursor()
        # namesテーブルにその名前が存在するか確認
        c.execute('SELECT 1 FROM names WHERE name = ?', (name,))
        if c.fetchone():
            # 存在すれば、facesテーブルに画像を追加
            c.execute('INSERT INTO faces (name, face_image) VALUES (?, ?)', (name, face_image))
            self.conn.commit()
            print(f"既存の人物 '{name}' に新しい顔画像を追加しました。")
            return True
        else:
            # 存在しなければ、失敗を返す
            print(f"[エラー] 既存の人物 '{name}' が見つかりませんでした。")
            return False
        
    def get_all_faces_for_training(self):
        c = self.conn.cursor()
        c.execute('SELECT label, name FROM names ORDER BY label')
        names = dict(c.fetchall())
        
        c.execute('SELECT n.label, f.face_image FROM faces f JOIN names n ON f.name = n.name')
        rows = c.fetchall()
        
        faces = [row[1] for row in rows]
        labels = [row[0] for row in rows]
        
        return faces, np.array(labels), names

    def get_all_names(self):
        """【新規】登録されているすべての名前を取得する"""
        c = self.conn.cursor()
        c.execute('SELECT name FROM names ORDER BY name')
        return [row[0] for row in c.fetchall()]

    def delete_person_by_name(self, name):
        """【新規】指定された名前の人物データをすべて削除する"""
        c = self.conn.cursor()
        c.execute('DELETE FROM faces WHERE name = ?', (name,))
        c.execute('DELETE FROM names WHERE name = ?', (name,))
        self.conn.commit()

    def delete_all(self):
        c = self.conn.cursor()
        c.execute('DELETE FROM faces')
        c.execute('DELETE FROM names')
        # SQLiteのシーケンスもリセットしてlabelが1から始まるようにする
        c.execute('DELETE FROM sqlite_sequence WHERE name="names"')
        self.conn.commit()

    def close(self):
        """データベース接続を安全に閉じる"""
        if self.conn:
            self.conn.close()
            print("データベース接続を閉じました。")        

    def get_label_by_name(self, name):
        """指定された名前のID(label)を取得する"""
        c = self.conn.cursor()
        c.execute('SELECT label FROM names WHERE name = ?', (name,))
        result = c.fetchone()
        return result[0] if result else None
