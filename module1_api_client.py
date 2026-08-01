import cv2
import math
import time
import requests
import numpy as np
import mediapipe as mp

MODEL_PATH = "face_landmarker.task"
API_URL = "http://127.0.0.1:8000/api/predict"
TOTAL_SAMPLES = 5
CAPTURE_INTERVAL = 0.7
API_INTERVAL = 1.0

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
    base = distance(c, d)

    if base == 0:
        return 0.0

    return distance(a, b) / base

def extract_features(landmarks):
    return {
        "left_eye_open": ratio(
            landmarks[159],
            landmarks[145],
            landmarks[33],
            landmarks[133]
        ),
        "right_eye_open": ratio(
            landmarks[386],
            landmarks[374],
            landmarks[362],
            landmarks[263]
        ),
        "mouth_open": ratio(
            landmarks[13],
            landmarks[14],
            landmarks[61],
            landmarks[291]
        ),
        "mouth_width": ratio(
            landmarks[61],
            landmarks[291],
            landmarks[234],
            landmarks[454]
        ),
        "left_brow_eye": ratio(
            landmarks[105],
            landmarks[159],
            landmarks[33],
            landmarks[133]
        ),
        "right_brow_eye": ratio(
            landmarks[334],
            landmarks[386],
            landmarks[362],
            landmarks[263]
        )
    }

def average_features(samples):
    return {
        key: float(
            np.mean([sample[key] for sample in samples])
        )
        for key in samples[0]
    }

def send_frame_to_api(frame):
    success, encoded_image = cv2.imencode(".jpg", frame)

    if not success:
        return None, "Image encode failed"

    try:
        response = requests.post(
            API_URL,
            files={
                "file": (
                    "frame.jpg",
                    encoded_image.tobytes(),
                    "image/jpeg"
                )
            },
            timeout=10
        )

        response.raise_for_status()

        return response.json(), None

    except requests.RequestException as error:
        return None, str(error)

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Cannot open camera")
    raise SystemExit

samples = []
baseline = None
collecting = False
countdown_start = 0.0
last_capture = 0.0
last_api_time = 0.0

status = "Press C for new user"
api_status = "Not connected"
api_result = None
emotion_label = "--"
emotion_confidence = 0.0

with FaceLandmarker.create_from_options(options) as landmarker:

    while True:

        ret, frame = camera.read()

        if not ret:
            print("Cannot read camera")
            break

        frame = cv2.flip(frame, 1)
        clean_frame = frame.copy()

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

        if result.face_landmarks:

            landmarks = result.face_landmarks[0]
            current = extract_features(landmarks)

            height, width, _ = frame.shape

            xs = [
                int(point.x * width)
                for point in landmarks
            ]

            ys = [
                int(point.y * height)
                for point in landmarks
            ]

            x1 = max(min(xs) - 10, 0)
            y1 = max(min(ys) - 10, 0)
            x2 = min(max(xs) + 10, width - 1)
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

                px = int(point.x * width)
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
                status = "No face"

            elif time.time() - last_capture >= CAPTURE_INTERVAL:

                samples.append(current)

                last_capture = time.time()

                status = (
                    f"Sample "
                    f"{len(samples)}/{TOTAL_SAMPLES}"
                )

                if len(samples) >= TOTAL_SAMPLES:

                    baseline = average_features(samples)

                    samples.clear()

                    collecting = False

                    status = "Personal Baseline Ready"

                    print("Personal Baseline Ready")

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

            if time.time() - last_api_time >= API_INTERVAL:

                api_result, api_error = send_frame_to_api(
                    clean_frame
                )

                last_api_time = time.time()

                if api_result is not None:

                    api_status = "Connected"

                    emotion_data = api_result.get(
                        "emotion",
                        {}
                    )

                    emotion_label = str(
                        emotion_data.get(
                            "label",
                            "--"
                        )
                    )

                    emotion_confidence = float(
                        emotion_data.get(
                            "confidence",
                            0.0
                        )
                    )

                    print(
                        "Emotion:",
                        emotion_label,
                        f"{emotion_confidence * 100:.1f}%"
                    )

                else:

                    api_status = "Connection failed"

                    print(
                        "API error:",
                        api_error
                    )

        y = 135

        if difference is not None:

            for key in difference:

                text = (
                    f"{key}: "
                    f"B={baseline[key]:.3f} "
                    f"C={current[key]:.3f} "
                    f"D={difference[key]:+.3f}"
                )

                cv2.putText(
                    frame,
                    text,
                    (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (0, 255, 255),
                    1
                )

                y += 25

        cv2.putText(
            frame,
            "C : New User Baseline",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            "R : Reset User",
            (20, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            "Q : Quit",
            (20, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            "Status : " + status,
            (20, 115),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (
                (0, 255, 0)
                if baseline is not None
                else (0, 255, 255)
            ),
            2
        )

        cv2.putText(
            frame,
            "API : " + api_status,
            (20, 310),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (
                (0, 255, 0)
                if api_status == "Connected"
                else (0, 0, 255)
            ),
            2
        )

        cv2.putText(
            frame,
            "Emotion : " + emotion_label,
            (20, 340),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            (
                "Confidence : "
                f"{emotion_confidence * 100:.1f}%"
            ),
            (20, 370),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        cv2.imshow(
            "Module 1 - API Client",
            frame
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("c") and not collecting:

            if landmarks is None:

                status = "No face"

            else:

                baseline = None

                samples.clear()

                collecting = True

                countdown_start = time.time()

                last_capture = 0.0

                last_api_time = 0.0

                api_result = None

                emotion_label = "--"

                emotion_confidence = 0.0

                status = "Starting new user"

        elif key == ord("r"):

            baseline = None

            samples.clear()

            collecting = False

            last_api_time = 0.0

            api_result = None

            emotion_label = "--"

            emotion_confidence = 0.0

            api_status = "Not connected"

            status = "User data cleared"

            print("User data cleared")

        elif key == ord("q"):

            break

camera.release()

cv2.destroyAllWindows()

samples.clear()

baseline = None

print("Program ended. All user data cleared.")