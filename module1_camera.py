import cv2
import os
import time

SAVE_DIR = "calibration"
os.makedirs(SAVE_DIR, exist_ok=True)

face_detector = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Cannot open camera")
    exit()

status = "Ready"
calibrating = False
photo_count = 0
countdown_start = 0
last_capture = 0

while True:
    ret, frame = camera.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    clean = frame.copy()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(120,120)
    )

    face_img = None

    if len(faces) > 0:
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])

        cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 2)
        cv2.putText(frame,"Face",(x,y-10),
                    cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,255,0),2)

        face_img = clean[y:y+h, x:x+w]

    if calibrating:
        t = time.time() - countdown_start

        if t < 1:
            status = "3"
        elif t < 2:
            status = "2"
        elif t < 3:
            status = "1"
        else:
            status = "Capturing..."

            if face_img is not None and time.time()-last_capture > 0.5:
                photo_count += 1

                face = cv2.resize(face_img, (224,224))
                filename = os.path.join(SAVE_DIR, f"face{photo_count}.jpg")
                cv2.imwrite(filename, face)

                last_capture = time.time()
                status = f"Capture {photo_count}/5"

                if photo_count >= 5:
                    calibrating = False
                    status = "Calibration Success"

    cv2.putText(frame,"C : Calibration",(20,30),
                cv2.FONT_HERSHEY_SIMPLEX,0.7,(255,255,255),2)

    cv2.putText(frame,"Q : Quit",(20,60),
                cv2.FONT_HERSHEY_SIMPLEX,0.7,(255,255,255),2)

    cv2.putText(frame,"Status : " + status,(20,95),
                cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,255),2)

    cv2.imshow("Module 1 - Input & Calibration", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("c") and not calibrating:
        if face_img is not None:
            calibrating = True
            photo_count = 0
            countdown_start = time.time()
            last_capture = 0
            status = "Calibration Start"
        else:
            status = "No Face"

    if key == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()