import cv2
import json
import math
import time
import numpy as np
import mediapipe as mp

MODEL_PATH = "face_landmarker.task"
BASELINE_PATH = "baseline.json"
TOTAL_SAMPLES = 5
CAPTURE_INTERVAL = 0.7

BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
RunningMode = mp.tasks.vision.RunningMode

options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=RunningMode.VIDEO,
    num_faces=1,
    min_face_detection_confidence=0.5,
    min_face_presence_confidence=0.5,
    min_tracking_confidence=0.5
)

def distance(a, b):
    return math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2 + (a.z-b.z)**2)

def ratio(a, b, c, d):
    value = distance(c, d)
    return 0.0 if value == 0 else distance(a, b) / value

def extract_features(landmarks):
    return {
        "left_eye_open": ratio(landmarks[159], landmarks[145], landmarks[33], landmarks[133]),
        "right_eye_open": ratio(landmarks[386], landmarks[374], landmarks[362], landmarks[263]),
        "mouth_open": ratio(landmarks[13], landmarks[14], landmarks[61], landmarks[291]),
        "mouth_width": ratio(landmarks[61], landmarks[291], landmarks[234], landmarks[454]),
        "left_brow_eye": ratio(landmarks[105], landmarks[159], landmarks[33], landmarks[133]),
        "right_brow_eye": ratio(landmarks[334], landmarks[386], landmarks[362], landmarks[263])
    }

def average_features(samples):
    return {
        key: float(np.mean([sample[key] for sample in samples]))
        for key in samples[0]
    }

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Cannot open camera")
    raise SystemExit

samples = []
collecting = False
countdown_start = 0.0
last_capture = 0.0
status = "Ready"

with FaceLandmarker.create_from_options(options) as landmarker:
    while True:
        ret, frame = camera.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        result = landmarker.detect_for_video(
            mp_image,
            int(time.time() * 1000)
        )

        landmarks = None

        if result.face_landmarks:
            landmarks = result.face_landmarks[0]
            h, w, _ = frame.shape
            xs = [int(p.x * w) for p in landmarks]
            ys = [int(p.y * h) for p in landmarks]

            cv2.rectangle(
                frame,
                (max(min(xs)-10, 0), max(min(ys)-10, 0)),
                (min(max(xs)+10, w-1), min(max(ys)+10, h-1)),
                (0, 255, 0),
                2
            )

            for index in [33,133,145,159,263,362,374,386,13,14,61,291,105,334]:
                p = landmarks[index]
                cv2.circle(frame, (int(p.x*w), int(p.y*h)), 2, (0,255,255), -1)

        if collecting:
            elapsed = time.time() - countdown_start

            if elapsed < 1:
                status = "3"
            elif elapsed < 2:
                status = "2"
            elif elapsed < 3:
                status = "1"
            elif landmarks is None:
                status = "No face"
            elif time.time() - last_capture >= CAPTURE_INTERVAL:
                samples.append(extract_features(landmarks))
                last_capture = time.time()
                status = f"Sample {len(samples)}/{TOTAL_SAMPLES}"

                if len(samples) >= TOTAL_SAMPLES:
                    baseline = average_features(samples)

                    with open(BASELINE_PATH, "w", encoding="utf-8") as file:
                        json.dump(baseline, file, ensure_ascii=False, indent=2)

                    print("Personal Baseline Created")
                    print(json.dumps(baseline, ensure_ascii=False, indent=2))

                    samples.clear()
                    collecting = False
                    status = "Personal Baseline Created"

        cv2.putText(frame, "C : Create Baseline", (20,30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        cv2.putText(frame, "Q : Quit", (20,60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        cv2.putText(frame, "Status : " + status, (20,95),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0,255,255), 2)

        cv2.imshow("Module 1 - Landmark Baseline", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("c") and not collecting:
            if landmarks is None:
                status = "No face"
            else:
                samples.clear()
                collecting = True
                countdown_start = time.time()
                last_capture = 0.0
                status = "Starting"

        elif key == ord("q"):
            break

camera.release()
cv2.destroyAllWindows()
