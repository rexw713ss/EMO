"""
四階段漸進式情緒辨識引擎
Stage 1: Baseline FER (fer 套件直接辨識)
Stage 2: FER + MediaPipe (臉部關鍵點輔助修正)
Stage 3: Fine-tuned Model (EfficientNetV2B0 微調)
Stage 4: Final System (滑動平均 + 情緒趨勢分析)
"""

import time
import numpy as np
import cv2
from collections import deque
from pathlib import Path


DEFAULT_FACE_LANDMARKER_PATH = Path(__file__).resolve().with_name("face_landmarker.task")


def _create_face_landmarker(model_path=None):
    """建立 MediaPipe Tasks Face Landmarker（相容 MediaPipe 0.10.30+）。"""
    import mediapipe as mp

    path = Path(model_path or DEFAULT_FACE_LANDMARKER_PATH)
    if not path.is_file():
        raise FileNotFoundError(
            f"找不到 MediaPipe Face Landmarker 模型：{path}。"
            "請將 face_landmarker.task 放在 emotion_system.py 同一資料夾。"
        )

    options = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(path)),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
    return mp, landmarker


# ============================================================
# Stage 1: Baseline FER
# ============================================================
class Stage1_BaselineFER:
    """直接使用 fer 套件做情緒辨識。"""

    def __init__(self):
        from fer.fer import FER
        self.detector = FER(mtcnn=True)
        self.name = "Stage 1: Baseline FER"

    def predict(self, frame):
        """
        Returns:
            result: dict with keys:
                - emotion: str
                - confidence: float
                - all_scores: dict {emotion: score}
                - bbox: (x, y, w, h) or None
                - latency_ms: float
        """
        t0 = time.perf_counter()
        emotions = self.detector.detect_emotions(frame)
        latency = (time.perf_counter() - t0) * 1000

        if not emotions:
            return {
                "emotion": "unknown", "confidence": 0.0,
                "all_scores": {}, "bbox": None,
                "latency_ms": latency
            }

        face = emotions[0]
        scores = face["emotions"]
        top_emotion = max(scores, key=scores.get)
        return {
            "emotion": top_emotion,
            "confidence": scores[top_emotion],
            "all_scores": scores,
            "bbox": tuple(face["box"]),
            "latency_ms": latency
        }


# ============================================================
# Stage 2: FER + MediaPipe Features
# ============================================================
class Stage2_FERWithMediaPipe:
    """FER 預測 + MediaPipe Face Mesh 臉部特徵輔助修正。"""

    # MediaPipe Face Mesh landmark indices
    # 嘴角
    LEFT_MOUTH = 61
    RIGHT_MOUTH = 291
    TOP_LIP = 13
    BOTTOM_LIP = 14
    # 眉毛
    LEFT_EYEBROW_INNER = 107
    LEFT_EYEBROW_OUTER = 70
    RIGHT_EYEBROW_INNER = 336
    RIGHT_EYEBROW_OUTER = 300
    # 眼睛
    LEFT_EYE_TOP = 159
    LEFT_EYE_BOTTOM = 145
    RIGHT_EYE_TOP = 386
    RIGHT_EYE_BOTTOM = 374
    # 臉部參考點 (用於頭部角度估算)
    NOSE_TIP = 1
    CHIN = 152
    LEFT_CHEEK = 234
    RIGHT_CHEEK = 454
    FOREHEAD = 10

    def __init__(self, face_landmarker_path=None):
        from fer.fer import FER

        self.detector = FER(mtcnn=True)
        self.mp, self.face_landmarker = _create_face_landmarker(face_landmarker_path)
        self.name = "Stage 2: FER + MediaPipe"
        self._prev_predictions = deque(maxlen=10)

    def _get_landmark_point(self, landmarks, idx, h, w):
        # Tasks API 回傳 list；舊 Solutions API 則回傳含 landmark 屬性的物件。
        points = getattr(landmarks, "landmark", landmarks)
        lm = points[idx]
        return np.array([lm.x * w, lm.y * h, lm.z * w])

    def _detect_face_landmarks(self, rgb):
        mp_image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
        result = self.face_landmarker.detect(mp_image)
        return result.face_landmarks[0] if result.face_landmarks else None

    def close(self):
        self.face_landmarker.close()

    def _compute_face_features(self, landmarks, h, w):
        """計算臉部 Action Unit 特徵。"""
        gp = lambda idx: self._get_landmark_point(landmarks, idx, h, w)

        # Mouth Aspect Ratio (MAR) - 嘴巴張開程度
        mouth_v = np.linalg.norm(gp(self.TOP_LIP) - gp(self.BOTTOM_LIP))
        mouth_h = np.linalg.norm(gp(self.LEFT_MOUTH) - gp(self.RIGHT_MOUTH))
        mar = mouth_v / (mouth_h + 1e-6)

        # 嘴角上揚比 (mouth corners vs lip center)
        mouth_center_y = (gp(self.TOP_LIP)[1] + gp(self.BOTTOM_LIP)[1]) / 2
        left_corner_y = gp(self.LEFT_MOUTH)[1]
        right_corner_y = gp(self.RIGHT_MOUTH)[1]
        smile_ratio = (mouth_center_y - (left_corner_y + right_corner_y) / 2) / (mouth_h + 1e-6)

        # Eyebrow Raise (眉毛高度 - 相對於眼睛)
        left_brow_h = gp(self.LEFT_EYE_TOP)[1] - gp(self.LEFT_EYEBROW_INNER)[1]
        right_brow_h = gp(self.RIGHT_EYE_TOP)[1] - gp(self.RIGHT_EYEBROW_INNER)[1]
        brow_raise = (left_brow_h + right_brow_h) / (2 * h + 1e-6)

        # Eye Aspect Ratio (EAR) - 眼睛開合度
        left_ear = np.linalg.norm(gp(self.LEFT_EYE_TOP) - gp(self.LEFT_EYE_BOTTOM))
        right_ear = np.linalg.norm(gp(self.RIGHT_EYE_TOP) - gp(self.RIGHT_EYE_BOTTOM))
        ear = (left_ear + right_ear) / (2 * mouth_h + 1e-6)

        # 頭部角度估算 (簡易版 - 用 nose tip 相對臉部中心)
        nose = gp(self.NOSE_TIP)
        left_cheek = gp(self.LEFT_CHEEK)
        right_cheek = gp(self.RIGHT_CHEEK)
        chin = gp(self.CHIN)
        forehead = gp(self.FOREHEAD)

        face_center_x = (left_cheek[0] + right_cheek[0]) / 2
        face_center_y = (forehead[1] + chin[1]) / 2
        face_width = np.linalg.norm(left_cheek[:2] - right_cheek[:2])
        face_height = np.linalg.norm(forehead[:2] - chin[:2])

        yaw = (nose[0] - face_center_x) / (face_width + 1e-6)  # 左右轉
        pitch = (nose[1] - face_center_y) / (face_height + 1e-6)  # 上下點頭

        return {
            "mar": float(mar),
            "smile_ratio": float(smile_ratio),
            "brow_raise": float(brow_raise),
            "ear": float(ear),
            "yaw": float(yaw),
            "pitch": float(pitch),
        }

    def _correct_prediction(self, fer_scores, features):
        """用 MediaPipe 特徵修正 FER 預測。"""
        corrected = dict(fer_scores)

        # 規則 1: 嘴角上揚且 MAR 小 → 增加 happy 權重
        if features["smile_ratio"] > 0.05 and features["mar"] < 0.3:
            corrected["happy"] = corrected.get("happy", 0) * 1.3

        # 規則 2: 眉毛明顯上揚 + 嘴巴大開 → 增加 surprise 權重
        if features["brow_raise"] > 0.02 and features["mar"] > 0.4:
            corrected["surprise"] = corrected.get("surprise", 0) * 1.3

        # 規則 3: 眉毛皺緊（brow_raise 低）→ 增加 anger 權重
        if features["brow_raise"] < 0.005:
            corrected["angry"] = corrected.get("angry", 0) * 1.2

        # 規則 4: 頭部大幅偏轉 → 降低信心（可能是側臉誤判）
        if abs(features["yaw"]) > 0.15:
            for k in corrected:
                corrected[k] *= 0.8
            corrected["neutral"] = corrected.get("neutral", 0) + 0.1

        # 正規化
        total = sum(corrected.values()) + 1e-6
        corrected = {k: v / total for k, v in corrected.items()}

        return corrected

    def predict(self, frame):
        t0 = time.perf_counter()

        # FER 預測
        emotions = self.detector.detect_emotions(frame)

        # MediaPipe 特徵
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        landmarks = self._detect_face_landmarks(rgb)

        latency = (time.perf_counter() - t0) * 1000

        if not emotions:
            return {
                "emotion": "unknown", "confidence": 0.0,
                "all_scores": {}, "bbox": None,
                "features": {}, "latency_ms": latency,
                "stability": 0.0
            }

        face = emotions[0]
        fer_scores = face["emotions"]
        bbox = tuple(face["box"])

        # 提取 MediaPipe 特徵並修正
        features = {}
        if landmarks is not None:
            h, w = frame.shape[:2]
            features = self._compute_face_features(landmarks, h, w)
            corrected = self._correct_prediction(fer_scores, features)
        else:
            corrected = fer_scores

        top_emotion = max(corrected, key=corrected.get)

        # 計算穩定度 (最近 N 幀預測一致率)
        self._prev_predictions.append(top_emotion)
        if len(self._prev_predictions) >= 3:
            most_common = max(set(self._prev_predictions), key=list(self._prev_predictions).count)
            stability = list(self._prev_predictions).count(most_common) / len(self._prev_predictions)
        else:
            stability = 1.0

        return {
            "emotion": top_emotion,
            "confidence": corrected[top_emotion],
            "all_scores": corrected,
            "bbox": bbox,
            "features": features,
            "latency_ms": latency,
            "stability": stability
        }


# ============================================================
# Stage 3: Fine-tuned Model
# ============================================================
class Stage3_FineTuned:
    """使用自建微調模型 (EfficientNetV2B0) 進行推理。"""

    def __init__(self, model_path, class_names_path, face_landmarker_path=None,
                 use_tta=False):
        import tensorflow as tf

        self.model = tf.keras.models.load_model(model_path)
        self._infer = tf.function(
            lambda inputs: self.model(inputs, training=False),
            reduce_retracing=True,
            autograph=False,
        )
        self.class_names = list(np.load(class_names_path, allow_pickle=True))
        self.img_size = 224
        self.name = "Stage 3: Fine-tuned Model"
        self.use_tta = use_tta

        # 判斷模型預處理方式
        # EfficientNetV2 用 [0, 255]，MobileNetV2 用 [-1, 1]
        first_layer_name = self.model.layers[0].name.lower()
        if "efficientnet" in first_layer_name:
            self._preprocess_mode = "efficientnet"  # [0, 255]
        else:
            self._preprocess_mode = "mobilenet"  # [-1, 1]

        # 新版 MediaPipe Tasks Face Landmarker，同時提供臉部定位與關鍵點。
        self.mp, self.face_landmarker = _create_face_landmarker(face_landmarker_path)
        self._prev_predictions = deque(maxlen=10)

    def _detect_face_bbox(self, rgb):
        mp_image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
        result = self.face_landmarker.detect(mp_image)
        if not result.face_landmarks:
            return None

        landmarks = result.face_landmarks[0]
        h, w = rgb.shape[:2]
        xs = [landmark.x * w for landmark in landmarks]
        ys = [landmark.y * h for landmark in landmarks]
        x1 = max(0, int(min(xs)))
        y1 = max(0, int(min(ys)))
        x2 = min(w, int(max(xs)) + 1)
        y2 = min(h, int(max(ys)) + 1)
        return x1, y1, x2 - x1, y2 - y1

    def close(self):
        self.face_landmarker.close()

    def _preprocess_face(self, face_img):
        face_resized = cv2.resize(face_img, (self.img_size, self.img_size))
        face_rgb = cv2.cvtColor(face_resized, cv2.COLOR_BGR2RGB)
        face_array = np.expand_dims(face_rgb, axis=0).astype(np.float32)

        if self._preprocess_mode == "mobilenet":
            import tensorflow as tf
            face_array = tf.keras.applications.mobilenet_v2.preprocess_input(face_array)
        # EfficientNetV2: 直接用 [0, 255]，不需額外處理

        return face_array

    def predict(self, frame):
        t0 = time.perf_counter()

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        detected_bbox = self._detect_face_bbox(rgb)

        if detected_bbox is None:
            latency = (time.perf_counter() - t0) * 1000
            return {
                "emotion": "unknown", "confidence": 0.0,
                "all_scores": {}, "bbox": None,
                "latency_ms": latency, "stability": 0.0
            }

        h, w = frame.shape[:2]
        x, y, bw, bh = detected_bbox

        # 擴大裁切範圍
        pad = int(max(bw, bh) * 0.15)
        x1, y1 = max(0, x - pad), max(0, y - pad)
        x2, y2 = min(w, x + bw + pad), min(h, y + bh + pad)

        face_img = frame[y1:y2, x1:x2]
        if face_img.size == 0:
            latency = (time.perf_counter() - t0) * 1000
            return {
                "emotion": "unknown", "confidence": 0.0,
                "all_scores": {}, "bbox": (x, y, bw, bh),
                "latency_ms": latency, "stability": 0.0
            }

        face_input = self._preprocess_face(face_img)
        # tf.function 編譯單張前向傳播，避免 model.predict 的資料管線固定成本。
        preds = np.asarray(self._infer(face_input))[0]
        if self.use_tta:
            # Accuracy Mode：原圖與水平翻轉影像機率平均。
            # 臉部表情大致左右對稱，能降低單側光線與姿態造成的波動。
            flipped_face = cv2.flip(face_img, 1)
            flipped_input = self._preprocess_face(flipped_face)
            flipped_preds = np.asarray(self._infer(flipped_input))[0]
            preds = (preds + flipped_preds) / 2.0
        latency = (time.perf_counter() - t0) * 1000

        scores = {name: float(preds[i]) for i, name in enumerate(self.class_names)}
        top_idx = np.argmax(preds)
        top_emotion = self.class_names[top_idx]

        self._prev_predictions.append(top_emotion)
        if len(self._prev_predictions) >= 3:
            most_common = max(set(self._prev_predictions), key=list(self._prev_predictions).count)
            stability = list(self._prev_predictions).count(most_common) / len(self._prev_predictions)
        else:
            stability = 1.0

        return {
            "emotion": top_emotion,
            "confidence": float(preds[top_idx]),
            "all_scores": scores,
            "bbox": (x, y, bw, bh),
            "latency_ms": latency,
            "stability": stability
        }


# ============================================================
# Stage 4: Final System (滑動平均 + 情緒趨勢)
# ============================================================
class Stage4_FinalSystem:
    """基於 Stage 3 模型，加上 EMA 平滑與情緒趨勢分析。"""

    def __init__(self, model_path, class_names_path, ema_alpha=0.3, window_size=30,
                 face_landmarker_path=None, use_tta=False):
        self.stage3 = Stage3_FineTuned(
            model_path,
            class_names_path,
            face_landmarker_path=face_landmarker_path,
            use_tta=use_tta,
        )
        self.name = "Stage 4: Final System"

        self.ema_alpha = ema_alpha
        self.window_size = window_size

        # 初始化所有類別的 EMA 機率
        self._ema_scores = {name: 1.0 / len(self.stage3.class_names)
                           for name in self.stage3.class_names}

        # 情緒歷史 (用於趨勢分析)
        self._emotion_history = deque(maxlen=300)  # 最近 300 幀
        self._current_emotion = "neutral"
        self._current_duration = 0
        self._transitions = deque(maxlen=20)  # 最近 20 次情緒轉換

    def close(self):
        self.stage3.close()

    def _update_ema(self, raw_scores):
        """指數移動平均更新。"""
        for k in self._ema_scores:
            raw_val = raw_scores.get(k, 0.0)
            self._ema_scores[k] = (self.ema_alpha * raw_val +
                                   (1 - self.ema_alpha) * self._ema_scores[k])

    def _analyze_trend(self, smoothed_emotion):
        """分析情緒趨勢。"""
        self._emotion_history.append(smoothed_emotion)

        # 更新持續時間與轉換偵測
        if smoothed_emotion == self._current_emotion:
            self._current_duration += 1
        else:
            if self._current_duration > 5:  # 忽略太短的片段
                self._transitions.append({
                    "from": self._current_emotion,
                    "to": smoothed_emotion,
                    "duration": self._current_duration,
                    "timestamp": time.time()
                })
            self._current_emotion = smoothed_emotion
            self._current_duration = 1

        # 計算最近 N 幀的情緒分佈
        recent = list(self._emotion_history)[-self.window_size:]
        distribution = {}
        for e in recent:
            distribution[e] = distribution.get(e, 0) + 1
        for k in distribution:
            distribution[k] /= len(recent)

        # 情緒穩定度 (dominant emotion 佔比)
        dominant = max(distribution, key=distribution.get)
        stability_score = distribution[dominant]

        return {
            "dominant_emotion": dominant,
            "duration_frames": self._current_duration,
            "distribution": distribution,
            "stability_score": stability_score,
            "recent_transitions": list(self._transitions)[-5:],
        }

    def predict(self, frame):
        # 先用 Stage 3 取得原始預測
        raw_result = self.stage3.predict(frame)

        if raw_result["emotion"] == "unknown":
            return {**raw_result, "trend": {}, "smoothed_scores": self._ema_scores.copy()}

        # EMA 平滑
        self._update_ema(raw_result["all_scores"])
        smoothed_emotion = max(self._ema_scores, key=self._ema_scores.get)
        smoothed_confidence = self._ema_scores[smoothed_emotion]

        # 趨勢分析
        trend = self._analyze_trend(smoothed_emotion)

        return {
            "emotion": smoothed_emotion,
            "confidence": smoothed_confidence,
            "all_scores": raw_result["all_scores"],
            "smoothed_scores": self._ema_scores.copy(),
            "bbox": raw_result["bbox"],
            "latency_ms": raw_result["latency_ms"],
            "stability": trend["stability_score"],
            "trend": trend
        }
