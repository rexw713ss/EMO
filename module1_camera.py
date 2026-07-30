"""LEGACY / OFFLINE camera diagnostic tool.

This module is not used by the React + FastAPI application. It opens a local
OpenCV window for camera and face-box testing only. It does not save frames or
create a personal calibration baseline.

Press C to start detection after a three-second countdown, S to stop detection,
and Q to quit.
"""

from __future__ import annotations

import time

import cv2


def main() -> None:
    face_detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        raise RuntimeError("Cannot open camera")

    status = "Ready (offline diagnostic)"
    countdown_started_at: float | None = None
    detection_enabled = False

    print("LEGACY / OFFLINE TOOL: frames remain in memory and are not saved.")

    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)

            if countdown_started_at is not None:
                elapsed = time.time() - countdown_started_at
                if elapsed < 3:
                    status = f"Starting in {3 - int(elapsed)}"
                else:
                    countdown_started_at = None
                    detection_enabled = True
                    status = "Detecting"

            if detection_enabled:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_detector.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(120, 120),
                )
                if len(faces) == 0:
                    status = "Detecting - no face"
                else:
                    x, y, width, height = max(
                        faces, key=lambda face: face[2] * face[3]
                    )
                    cv2.rectangle(
                        frame,
                        (x, y),
                        (x + width, y + height),
                        (0, 255, 0),
                        2,
                    )
                    cv2.putText(
                        frame,
                        "Face",
                        (x, max(20, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 255, 0),
                        2,
                    )
                    status = "Detecting - face found"

            cv2.putText(
                frame,
                "C: Start detection  S: Stop  Q: Quit",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                f"Status: {status}",
                (20, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 255),
                2,
            )
            cv2.imshow("LEGACY - Offline Camera Diagnostic", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("c") and countdown_started_at is None:
                countdown_started_at = time.time()
                detection_enabled = False
            elif key == ord("s"):
                countdown_started_at = None
                detection_enabled = False
                status = "Stopped"
            elif key == ord("q"):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
