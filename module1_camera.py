import cv2
import time
import numpy as np

TOTAL_PHOTOS = 5

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

calibration_frames = []
baseline = None

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

        x, y, w, h = max(faces, key=lambda f:f[2]*f[3])

        cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)

        cv2.putText(
            frame,
            "Face",
            (x,y-10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0,255,0),
            2
        )

        face_img = clean[y:y+h,x:x+w]

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

                face = cv2.resize(face_img,(224,224))

                calibration_frames.append(face)

                photo_count += 1

                last_capture = time.time()

                status = f"Capture {photo_count}/{TOTAL_PHOTOS}"

                if photo_count >= TOTAL_PHOTOS:

                    baseline = np.mean(
                        np.array(calibration_frames,dtype=np.float32),
                        axis=0
                    )

                    print("Personal Baseline Created")
                    print("Brightness:", np.mean(baseline))

                    calibrating = False
                    status = "Personal Baseline Created"

                    calibration_frames.clear()

    cv2.putText(
        frame,
        "C : Create Baseline",
        (20,30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255,255,255),
        2
    )

    cv2.putText(
        frame,
        "Q : Quit",
        (20,60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255,255,255),
        2
    )

    cv2.putText(
        frame,
        "Status : " + status,
        (20,95),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0,255,255),
        2
    )

    cv2.imshow(
        "Module 1 - Input & Calibration",
        frame
    )

    key = cv2.waitKey(1) & 0xFF

    if key == ord("c") and not calibrating:

        if face_img is not None:

            calibration_frames.clear()

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
