import cv2

print("OpenCVのカメラテストを開始します...")
print(f"OpenCVバージョン: {cv2.__version__}")

# カメラデバイスを開く (0はデフォルトのカメラ)
# cv2.CAP_DSHOW を追加するとWindowsで安定することがある
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# カメラが正常に開かれたかチェック
if not cap.isOpened():
    print("エラー: カメラを開けませんでした。")
    exit()

print("カメラを正常に開きました。ウィンドウが表示されます。")
print("ウィンドウが表示されたら、'q'キーを押すと終了します。")

while True:
    # 1フレーム読み込む
    ret, frame = cap.read()

    # フレームが正しく読み込めなかった場合はループを抜ける
    if not ret:
        print("エラー: フレームを読み込めませんでした。")
        break

    # フレームをウィンドウに表示
    cv2.imshow('Camera Test', frame)

    # 'q'キーが押されたらループを抜ける
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 後片付け
cap.release()
cv2.destroyAllWindows()
print("テストを終了します。")