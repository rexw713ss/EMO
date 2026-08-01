import cv2
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh
mp_draw = mp.solutions.drawing_utils
draw_style = mp.solutions.drawing_styles

camera = cv2.VideoCapture(0)

with mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as face_mesh:

    while True:
        ret, frame = camera.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = face_mesh.process(rgb)

        h, w, _ = frame.shape

        if result.multi_face_landmarks:
            for face_landmarks in result.multi_face_landmarks:

                # 畫整張 Face Mesh
                mp_draw.draw_landmarks(
                    image=frame,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=draw_style.get_default_face_mesh_tesselation_style()
                )

                # 計算外框
                xs = [int(lm.x * w) for lm in face_landmarks.landmark]
                ys = [int(lm.y * h) for lm in face_landmarks.landmark]

                x1, x2 = min(xs), max(xs)
                y1, y2 = min(ys), max(ys)

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)
                cv2.putText(frame, "Face Mesh",
                            (x1, y1-10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (0,255,0),
                            2)

        cv2.putText(frame, "Module 1 - Face Mesh",
                    (20,30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255,255,255),
                    2)

        cv2.putText(frame,
                    "Q : Quit",
                    (20,60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255,255,255),
                    2)

        cv2.imshow("Module1 FaceMesh", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

camera.release()
cv2.destroyAllWindows()