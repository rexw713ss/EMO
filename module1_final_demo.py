import cv2
import math
import time
import numpy as np
import mediapipe as mp

MODEL_PATH = "face_landmarker.task"
TOTAL_SAMPLES = 5
CAPTURE_INTERVAL = 0.7
PANEL_WIDTH = 300

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
    return math.sqrt(
        (a.x - b.x) ** 2 +
        (a.y - b.y) ** 2 +
        (a.z - b.z) ** 2
    )

def ratio(a, b, c, d):
    denominator = distance(c, d)

    if denominator == 0:
        return 0.0

    return distance(a, b) / denominator

def extract_features(landmarks):
    return {
        "left_eye_open": ratio(
            landmarks[159], landmarks[145],
            landmarks[33], landmarks[133]
        ),
        "right_eye_open": ratio(
            landmarks[386], landmarks[374],
            landmarks[362], landmarks[263]
        ),
        "mouth_open": ratio(
            landmarks[13], landmarks[14],
            landmarks[61], landmarks[291]
        ),
        "mouth_width": ratio(
            landmarks[61], landmarks[291],
            landmarks[234], landmarks[454]
        ),
        "left_brow_eye": ratio(
            landmarks[105], landmarks[159],
            landmarks[33], landmarks[133]
        ),
        "right_brow_eye": ratio(
            landmarks[334], landmarks[386],
            landmarks[362], landmarks[263]
        )
    }

def average_features(samples):
    return {
        key: float(np.mean([sample[key] for sample in samples]))
        for key in samples[0]
    }

def feature_label(key):
    labels = {
        "left_eye_open": "Left Eye",
        "right_eye_open": "Right Eye",
        "mouth_open": "Mouth Open",
        "mouth_width": "Mouth Width",
        "left_brow_eye": "Left Brow",
        "right_brow_eye": "Right Brow"
    }

    return labels.get(key, key)

def feature_state(value):
    if value > 0.05:
        return "Higher"

    if value < -0.05:
        return "Lower"

    return "Stable"

def create_display(frame):
    height, width, _ = frame.shape

    panel = np.full(
        (height, PANEL_WIDTH, 3),
        (20, 20, 20),
        dtype=np.uint8
    )

    return np.hstack((frame, panel))

def draw_panel(
    display,
    camera_width,
    user_id,
    status,
    face_detected,
    baseline_ready,
    difference
):
    panel_x = camera_width
    height, width, _ = display.shape

    cv2.putText(
        display,
        "Emotion Recognition",
        (panel_x + 20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        display,
        f"User : {user_id:03d}",
        (panel_x + 20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )

    face_text = "Detected" if face_detected else "Not Detected"
    face_color = (0, 255, 0) if face_detected else (0, 0, 255)

    cv2.putText(
        display,
        "Face : " + face_text,
        (panel_x + 20, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        face_color,
        2
    )

    baseline_text = "Ready" if baseline_ready else "Not Ready"
    baseline_color = (0, 255, 0) if baseline_ready else (0, 255, 255)

    cv2.putText(
        display,
        "Baseline : " + baseline_text,
        (panel_x + 20, 145),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        baseline_color,
        2
    )

    cv2.putText(
        display,
        "Status : " + status,
        (panel_x + 20, 180),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (0, 255, 255),
        1
    )

    cv2.line(
        display,
        (panel_x + 20, 200),
        (width - 20, 200),
        (100, 100, 100),
        1
    )

    cv2.putText(
        display,
        "Calibration Result",
        (panel_x + 20, 230),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )

    y = 265

    if difference is None:
        cv2.putText(
            display,
            "No baseline data",
            (panel_x + 20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (180, 180, 180),
            1
        )
    else:
        for key, value in difference.items():
            cv2.putText(
                display,
                f"{feature_label(key)} : {value:+.3f}",
                (panel_x + 20, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 255, 255),
                1
            )

            cv2.putText(
                display,
                feature_state(value),
                (width - 90, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                (0, 255, 0),
                1
            )

            y += 32

    cv2.putText(
        display,
        "C : Create Baseline",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        display,
        "R : Next User",
        (20, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        display,
        "Q : Quit",
        (20, 90),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Cannot open camera")
    raise SystemExit

samples = []
baseline = None
collecting = False
countdown_start = 0.0
last_capture = 0.0
status = "Press C to create baseline"
user_id = 1

with FaceLandmarker.create_from_options(options) as landmarker:
    while True:
        ret, frame = camera.read()

        if not ret:
            print("Cannot read camera")
            break

        frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )

        result = landmarker.detect_for_video(
            mp_image,
            int(time.time() * 1000)
        )

        landmarks = None
        current = None
        difference = None
        face_detected = False

        height, camera_width, _ = frame.shape

        if result.face_landmarks:
            face_detected = True
            landmarks = result.face_landmarks[0]
            current = extract_features(landmarks)

            xs = [
                int(point.x * camera_width)
                for point in landmarks
            ]

            ys = [
                int(point.y * height)
                for point in landmarks
            ]

            x1 = max(min(xs) - 10, 0)
            y1 = max(min(ys) - 10, 0)
            x2 = min(max(xs) + 10, camera_width - 1)
            y2 = min(max(ys) + 10, height - 1)

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            for index in [
                33, 133, 145, 159,
                263, 362, 374, 386,
                13, 14, 61, 291,
                105, 334
            ]:
                point = landmarks[index]
                px = int(point.x * camera_width)
                py = int(point.y * height)

                cv2.circle(
                    frame,
                    (px, py),
                    2,
                    (0, 255, 255),
                    -1
                )

        if collecting:
            elapsed = time.time() - countdown_start

            if elapsed < 1:
                status = "3"

            elif elapsed < 2:
                status = "2"

            elif elapsed < 3:
                status = "1"

            elif landmarks is None:
                status = "No face detected"

            elif time.time() - last_capture >= CAPTURE_INTERVAL:
                samples.append(current)
                last_capture = time.time()
                status = f"Collecting {len(samples)}/{TOTAL_SAMPLES}"

                if len(samples) >= TOTAL_SAMPLES:
                    baseline = average_features(samples)
                    samples.clear()
                    collecting = False
                    status = "Baseline ready"

                    print(f"User {user_id:03d} baseline ready")

                    for key, value in baseline.items():
                        print(f"{key}: {value:.4f}")

        if (
            baseline is not None
            and current is not None
            and not collecting
        ):
            difference = {
                key: current[key] - baseline[key]
                for key in baseline
            }

        display = create_display(frame)

        draw_panel(
            display,
            camera_width,
            user_id,
            status,
            face_detected,
            baseline is not None,
            difference
        )

        cv2.imshow(
            "Module 1 - Final Demo",
            display
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("c") and not collecting:
            if landmarks is None:
                status = "No face detected"
            else:
                baseline = None
                samples.clear()
                collecting = True
                countdown_start = time.time()
                last_capture = 0.0
                status = "Starting baseline"

        elif key == ord("r"):
            user_id += 1
            baseline = None
            samples.clear()
            collecting = False
            countdown_start = 0.0
            last_capture = 0.0
            status = "Press C to create baseline"

            print(f"Switched to User {user_id:03d}")

        elif key == ord("q"):
            break

camera.release()
cv2.destroyAllWindows()

samples.clear()
baseline = None

print("Program ended. User data cleared.")
