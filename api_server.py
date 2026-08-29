"""React 可連線的即時情緒辨識 API。

啟動：
    uvicorn api_server:app --host 0.0.0.0 --port 8000

WebSocket 協定：
    Client -> Server: JPEG/PNG 二進位影格
    Server -> Client: JSON 情緒結果
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import sqlite3
import threading
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from emotion_system import Stage3_FineTuned


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = Path(os.getenv("EMOTION_MODEL_PATH", BASE_DIR / "emotion_model.keras"))
CLASS_NAMES_PATH = Path(os.getenv("EMOTION_CLASS_NAMES_PATH", BASE_DIR / "class_names.npy"))
MAX_FRAME_BYTES = int(os.getenv("EMOTION_MAX_FRAME_BYTES", "2500000"))
MAX_FRAME_DIMENSION = int(os.getenv("EMOTION_MAX_FRAME_DIMENSION", "1280"))
DEFAULT_TTA = os.getenv("EMOTION_TTA", "false").lower() in {"1", "true", "yes", "on"}
TF_INTRA_OP_THREADS = int(os.getenv("EMOTION_TF_INTRA_OP_THREADS", "4"))
TF_INTER_OP_THREADS = int(os.getenv("EMOTION_TF_INTER_OP_THREADS", "1"))
DATABASE_PATH = Path(
    os.getenv("EMOTION_DATABASE_PATH", BASE_DIR / "data" / "emotion_sessions.db")
)
MODEL_EVAL_PATH = Path(
    os.getenv("EMOTION_MODEL_EVAL_PATH", BASE_DIR / "data" / "model_eval.json")
)

MODEL_EMOTION_CLASSES = (
    "anger",
    "contempt",
    "disgust",
    "fear",
    "happy",
    "neutral",
    "sad",
    "surprise",
)

VISUAL_STATE_GROUPS = {
    "calm": ("neutral",),
    "pleasant": ("happy",),
    "alert": ("anger", "fear", "surprise"),
    "low": ("sad", "contempt", "disgust"),
}

VISUAL_STATE_LABELS = {
    "calm": "平靜",
    "pleasant": "愉悅",
    "alert": "緊張",
    "low": "低落",
    "unknown": "未偵測",
}

_mapped_model_classes = [
    emotion
    for grouped_emotions in VISUAL_STATE_GROUPS.values()
    for emotion in grouped_emotions
]
if (
    len(_mapped_model_classes) != len(set(_mapped_model_classes))
    or set(_mapped_model_classes) != set(MODEL_EMOTION_CLASSES)
):
    raise RuntimeError("八類模型情緒必須各自且僅能映射到一個四類視覺狀態")


class EmotionSessionCreate(BaseModel):
    participant_code: str = Field(min_length=1, max_length=64)
    display_name: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=500)
    started_at_ms: int = Field(gt=0)
    ended_at_ms: int = Field(gt=0)
    sample_count: int = Field(ge=0)
    face_detected_samples: int = Field(ge=0)
    dominant_visual_state: Literal["calm", "pleasant", "alert", "low", "unknown"]
    average_scores: dict[str, float]


@contextmanager
def database_connection():
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    """建立本機 SQLite；只保存工作階段摘要與使用者輸入，不保存影像。"""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with database_connection() as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS emotion_sessions (
                id TEXT PRIMARY KEY,
                participant_code TEXT NOT NULL,
                display_name TEXT,
                note TEXT,
                started_at_ms INTEGER NOT NULL,
                ended_at_ms INTEGER NOT NULL,
                sample_count INTEGER NOT NULL,
                face_detected_samples INTEGER NOT NULL,
                dominant_visual_state TEXT NOT NULL,
                average_scores_json TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_emotion_sessions_created_at
            ON emotion_sessions(created_at_ms DESC)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS visual_state_events (
                id TEXT PRIMARY KEY,
                visual_state TEXT NOT NULL,
                started_at_ms INTEGER NOT NULL,
                ended_at_ms INTEGER NOT NULL,
                duration_ms INTEGER NOT NULL,
                avg_confidence REAL NOT NULL,
                created_at_ms INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_visual_state_events_ended_at
            ON visual_state_events(ended_at_ms DESC)
            """
        )


def _normalize_session_payload(payload: EmotionSessionCreate) -> dict[str, Any]:
    participant_code = payload.participant_code.strip()
    if not participant_code:
        raise ValueError("使用者編號不可只包含空白")
    if payload.ended_at_ms < payload.started_at_ms:
        raise ValueError("結束時間不可早於開始時間")
    if payload.face_detected_samples > payload.sample_count:
        raise ValueError("偵測到人臉的樣本數不可大於總樣本數")

    scores: dict[str, float] = {}
    for emotion in MODEL_EMOTION_CLASSES:
        value = float(payload.average_scores.get(emotion, 0.0))
        if not math.isfinite(value) or value < 0.0 or value > 1.0:
            raise ValueError(f"{emotion} 平均分數必須介於 0 到 1")
        scores[emotion] = value

    return {
        "participant_code": participant_code,
        "display_name": payload.display_name.strip() if payload.display_name else None,
        "note": payload.note.strip() if payload.note else None,
        "started_at_ms": payload.started_at_ms,
        "ended_at_ms": payload.ended_at_ms,
        "sample_count": payload.sample_count,
        "face_detected_samples": payload.face_detected_samples,
        "dominant_visual_state": payload.dominant_visual_state,
        "average_scores": scores,
    }


def _row_to_session(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "participant_code": row["participant_code"],
        "display_name": row["display_name"],
        "note": row["note"],
        "started_at_ms": row["started_at_ms"],
        "ended_at_ms": row["ended_at_ms"],
        "sample_count": row["sample_count"],
        "face_detected_samples": row["face_detected_samples"],
        "dominant_visual_state": row["dominant_visual_state"],
        "average_scores": json.loads(row["average_scores_json"]),
        "created_at_ms": row["created_at_ms"],
    }


def create_stored_session(payload: EmotionSessionCreate) -> dict[str, Any]:
    normalized = _normalize_session_payload(payload)
    session_id = str(uuid.uuid4())
    created_at_ms = int(time.time() * 1000)
    with database_connection() as connection:
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            INSERT INTO emotion_sessions (
                id, participant_code, display_name, note,
                started_at_ms, ended_at_ms, sample_count,
                face_detected_samples, dominant_visual_state,
                average_scores_json, created_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                normalized["participant_code"],
                normalized["display_name"],
                normalized["note"],
                normalized["started_at_ms"],
                normalized["ended_at_ms"],
                normalized["sample_count"],
                normalized["face_detected_samples"],
                normalized["dominant_visual_state"],
                json.dumps(
                    normalized["average_scores"],
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                ),
                created_at_ms,
            ),
        )
        row = connection.execute(
            "SELECT * FROM emotion_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    if row is None:
        raise RuntimeError("資料庫寫入後無法讀回工作階段")
    return _row_to_session(row)


def list_stored_sessions(limit: int) -> list[dict[str, Any]]:
    with database_connection() as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT * FROM emotion_sessions
            ORDER BY created_at_ms DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_row_to_session(row) for row in rows]


def delete_stored_session(session_id: str) -> bool:
    with database_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM emotion_sessions WHERE id = ?",
            (session_id,),
        )
    return cursor.rowcount > 0


def persist_visual_state_event(event: dict[str, Any]) -> None:
    """背景寫入單一已完成的視覺狀態區間，供分佈摘要查詢使用。"""
    if event["duration_ms"] <= 0:
        return
    with database_connection() as connection:
        connection.execute(
            """
            INSERT INTO visual_state_events (
                id, visual_state, started_at_ms, ended_at_ms,
                duration_ms, avg_confidence, created_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                event["visual_state"],
                event["started_at_ms"],
                event["ended_at_ms"],
                event["duration_ms"],
                event["avg_confidence"],
                int(time.time() * 1000),
            ),
        )


def _start_of_range_ms(range_key: str) -> int:
    if range_key == "week":
        return int(time.time() * 1000) - 7 * 86_400_000
    start_of_today = datetime.now().astimezone().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int(start_of_today.timestamp() * 1000)


def compute_distribution(range_key: str) -> dict[str, Any]:
    start_ms = _start_of_range_ms(range_key)
    with database_connection() as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT visual_state, duration_ms, avg_confidence
            FROM visual_state_events
            WHERE ended_at_ms >= ?
            ORDER BY ended_at_ms ASC
            """,
            (start_ms,),
        ).fetchall()

    totals: dict[str, dict[str, float]] = {
        key: {"count": 0, "confidence_sum": 0.0, "duration_sum_ms": 0.0}
        for key in VISUAL_STATE_GROUPS
    }
    transition_counts: dict[tuple[str, str], int] = {}
    previous_state: str | None = None

    for row in rows:
        state = row["visual_state"]
        if state in totals:
            totals[state]["count"] += 1
            totals[state]["confidence_sum"] += float(row["avg_confidence"])
            totals[state]["duration_sum_ms"] += float(row["duration_ms"])
            if previous_state is not None and previous_state in totals:
                pair = (previous_state, state)
                transition_counts[pair] = transition_counts.get(pair, 0) + 1
            previous_state = state

    states = [
        {
            "key": key,
            "count": int(value["count"]),
            "avg_confidence": (
                value["confidence_sum"] / value["count"] if value["count"] else 0.0
            ),
            "avg_duration_ms": (
                value["duration_sum_ms"] / value["count"] if value["count"] else 0.0
            ),
        }
        for key, value in totals.items()
    ]

    top_transition = None
    if transition_counts:
        (from_key, to_key), count = max(
            transition_counts.items(), key=lambda item: item[1]
        )
        top_transition = {"from": from_key, "to": to_key, "count": count}

    return {"range": range_key, "states": states, "top_transition": top_transition}


def _allowed_origins() -> list[str]:
    configured = os.getenv(
        "EMOTION_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


ALLOWED_ORIGINS = _allowed_origins()


def decode_frame(data: bytes) -> np.ndarray:
    if not data:
        raise ValueError("影格內容為空")
    if len(data) > MAX_FRAME_BYTES:
        raise ValueError(f"影格超過限制：{len(data)} > {MAX_FRAME_BYTES} bytes")

    encoded = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("無法解碼影格，請傳送 JPEG 或 PNG")

    height, width = frame.shape[:2]
    largest = max(height, width)
    if largest > MAX_FRAME_DIMENSION:
        scale = MAX_FRAME_DIMENSION / largest
        frame = cv2.resize(
            frame,
            (max(1, int(width * scale)), max(1, int(height * scale))),
            interpolation=cv2.INTER_AREA,
        )
    return frame


class EmotionSession:
    """單一前端連線的 EMA 與情緒趨勢，不與其他使用者共用。"""

    def __init__(self, class_names: list[str], ema_alpha: float = 0.3, window_size: int = 30):
        self.class_names = [str(name) for name in class_names]
        self.ema_alpha = ema_alpha
        self.window_size = window_size
        self.reset()

    def reset(self) -> None:
        self.ema_scores = {name: 0.0 for name in self.class_names}
        self.initialized = False
        self.history: deque[str] = deque(maxlen=300)
        self.current_emotion = "unknown"
        self.current_duration = 0
        self.transitions: deque[dict[str, Any]] = deque(maxlen=20)
        self.current_visual_state = "unknown"
        self.visual_state_started_ms: int | None = None
        self.visual_state_confidence_sum = 0.0
        self.visual_state_sample_count = 0
        self.last_completed_visual_state_event: dict[str, Any] | None = None

    def _track_visual_state(self, key: str, confidence: float, now_ms: int) -> None:
        """追蹤四類視覺狀態的區間，供 /api/analytics/distribution 使用。"""
        if key != self.current_visual_state:
            if (
                self.current_visual_state in VISUAL_STATE_GROUPS
                and self.visual_state_started_ms is not None
                and self.visual_state_sample_count > 0
            ):
                self.last_completed_visual_state_event = {
                    "visual_state": self.current_visual_state,
                    "started_at_ms": self.visual_state_started_ms,
                    "ended_at_ms": now_ms,
                    "duration_ms": now_ms - self.visual_state_started_ms,
                    "avg_confidence": (
                        self.visual_state_confidence_sum
                        / self.visual_state_sample_count
                    ),
                }
            self.current_visual_state = key
            self.visual_state_started_ms = now_ms
            self.visual_state_confidence_sum = 0.0
            self.visual_state_sample_count = 0
        self.visual_state_confidence_sum += confidence
        self.visual_state_sample_count += 1

    def _update_ema(self, scores: dict[str, float]) -> None:
        if not self.initialized:
            self.ema_scores = {name: float(scores.get(name, 0.0)) for name in self.class_names}
            self.initialized = True
            return
        for name in self.class_names:
            raw = float(scores.get(name, 0.0))
            self.ema_scores[name] = (
                self.ema_alpha * raw + (1.0 - self.ema_alpha) * self.ema_scores[name]
            )

    def _visual_state(self) -> dict[str, Any]:
        grouped = {
            key: sum(self.ema_scores.get(label, 0.0) for label in labels)
            for key, labels in VISUAL_STATE_GROUPS.items()
        }
        total = sum(grouped.values())
        if total > 0:
            grouped = {key: value / total for key, value in grouped.items()}
        key = max(grouped, key=grouped.get) if grouped else "unknown"
        return {
            "key": key,
            "label": VISUAL_STATE_LABELS[key],
            "confidence": float(grouped.get(key, 0.0)),
            "scores": grouped,
        }

    def apply(self, raw: dict[str, Any]) -> dict[str, Any]:
        self.last_completed_visual_state_event = None
        now_ms = int(time.time() * 1000)
        raw_label = str(raw.get("emotion", "unknown"))
        if raw_label == "unknown" or not raw.get("all_scores"):
            self._track_visual_state("unknown", 0.0, now_ms)
            return {
                "face_detected": False,
                "emotion": {
                    "label": "unknown",
                    "confidence": 0.0,
                    "raw_label": "unknown",
                    "raw_confidence": 0.0,
                    "scores": {},
                    "smoothed_scores": dict(self.ema_scores),
                },
                "visual_state": {
                    "key": "unknown",
                    "label": VISUAL_STATE_LABELS["unknown"],
                    "confidence": 0.0,
                    "scores": {},
                },
                "trend": {
                    "dominant_emotion": self.current_emotion,
                    "duration_frames": self.current_duration,
                    "stability": 0.0,
                    "distribution": {},
                    "recent_transitions": list(self.transitions)[-5:],
                },
            }

        scores = {str(key): float(value) for key, value in raw["all_scores"].items()}
        self._update_ema(scores)
        emotion = max(self.ema_scores, key=self.ema_scores.get)
        confidence = float(self.ema_scores[emotion])
        self.history.append(emotion)

        if emotion == self.current_emotion:
            self.current_duration += 1
        else:
            if self.current_emotion != "unknown" and self.current_duration > 0:
                self.transitions.append({
                    "from": self.current_emotion,
                    "to": emotion,
                    "duration_frames": self.current_duration,
                    "timestamp_ms": int(time.time() * 1000),
                })
            self.current_emotion = emotion
            self.current_duration = 1

        recent = list(self.history)[-self.window_size:]
        distribution = {
            label: recent.count(label) / len(recent) for label in set(recent)
        }
        stability = max(distribution.values()) if distribution else 0.0

        visual_state_result = self._visual_state()
        self._track_visual_state(
            visual_state_result["key"], visual_state_result["confidence"], now_ms
        )

        return {
            "face_detected": True,
            "emotion": {
                "label": emotion,
                "confidence": confidence,
                "raw_label": raw_label,
                "raw_confidence": float(raw.get("confidence", 0.0)),
                "scores": scores,
                "smoothed_scores": dict(self.ema_scores),
            },
            "visual_state": visual_state_result,
            "trend": {
                "dominant_emotion": max(distribution, key=distribution.get),
                "duration_frames": self.current_duration,
                "stability": float(stability),
                "distribution": distribution,
                "recent_transitions": list(self.transitions)[-5:],
            },
        }


class EmotionService:
    """全服務共用一份模型；推論加鎖以保護 TensorFlow/MediaPipe 狀態。"""

    def __init__(self) -> None:
        if not MODEL_PATH.is_file():
            raise FileNotFoundError(f"找不到模型：{MODEL_PATH}")
        if not CLASS_NAMES_PATH.is_file():
            raise FileNotFoundError(f"找不到類別：{CLASS_NAMES_PATH}")

        import tensorflow as tf

        # 必須在建立模型或執行任何 TensorFlow op 前設定。0 代表交由 TF 自動決定。
        if TF_INTRA_OP_THREADS > 0:
            tf.config.threading.set_intra_op_parallelism_threads(TF_INTRA_OP_THREADS)
        if TF_INTER_OP_THREADS > 0:
            tf.config.threading.set_inter_op_parallelism_threads(TF_INTER_OP_THREADS)

        self.engine = Stage3_FineTuned(
            str(MODEL_PATH),
            str(CLASS_NAMES_PATH),
            use_tta=DEFAULT_TTA,
        )
        loaded_classes = tuple(str(name) for name in self.engine.class_names)
        if loaded_classes != MODEL_EMOTION_CLASSES:
            raise ValueError(
                "class_names.npy 與八類模型順序不符："
                f"expected={MODEL_EMOTION_CLASSES}, actual={loaded_classes}"
            )
        self.lock = threading.Lock()
        self.started_at = time.time()

        gpus = tf.config.list_physical_devices("GPU")
        self.device = gpus[0].name if gpus else "CPU"
        self.tensorflow_version = tf.__version__
        self.tf_intra_op_threads = tf.config.threading.get_intra_op_parallelism_threads()
        self.tf_inter_op_threads = tf.config.threading.get_inter_op_parallelism_threads()
        warmup_started = time.perf_counter()
        self._warm_up()
        self.warmup_ms = (time.perf_counter() - warmup_started) * 1000

    def _warm_up(self) -> None:
        """啟動時先建圖，避免第一位使用者承擔數秒初始化延遲。"""
        dummy_frame = np.full((480, 640, 3), 127, dtype=np.uint8)
        dummy_rgb = cv2.cvtColor(dummy_frame, cv2.COLOR_BGR2RGB)
        self.engine._detect_face_bbox(dummy_rgb)
        dummy_face = np.full((self.engine.img_size, self.engine.img_size, 3), 127, dtype=np.uint8)
        dummy_input = self.engine._preprocess_face(dummy_face)
        self.engine._infer(dummy_input)

    @property
    def class_names(self) -> list[str]:
        return [str(name) for name in self.engine.class_names]

    def predict(self, frame: np.ndarray, use_tta: bool) -> dict[str, Any]:
        with self.lock:
            self.engine.use_tta = use_tta
            return self.engine.predict(frame)

    def close(self) -> None:
        self.engine.close()


service: EmotionService | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global service
    await asyncio.to_thread(initialize_database)
    service = await asyncio.to_thread(EmotionService)
    try:
        yield
    finally:
        await asyncio.to_thread(service.close)
        service = None


app = FastAPI(
    title="Emotion Spectrum API",
    version="1.0.0",
    description="React 即時情緒辨識 WebSocket/HTTP API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


def require_service() -> EmotionService:
    if service is None:
        raise HTTPException(status_code=503, detail="模型尚未完成初始化")
    return service


def build_response(
    raw: dict[str, Any],
    session: EmotionSession,
    frame: np.ndarray,
    total_ms: float,
    accuracy_mode: bool,
) -> dict[str, Any]:
    current_service = require_service()
    result = session.apply(raw)
    bbox = raw.get("bbox")
    result.update({
        "type": "emotion",
        "schema_version": "1.0",
        "timestamp_ms": int(time.time() * 1000),
        "frame": {"width": int(frame.shape[1]), "height": int(frame.shape[0])},
        "bbox": (
            {"x": int(bbox[0]), "y": int(bbox[1]), "width": int(bbox[2]), "height": int(bbox[3])}
            if bbox else None
        ),
        "performance": {
            "inference_ms": float(raw.get("latency_ms", 0.0)),
            "server_ms": float(total_ms),
            "device": current_service.device,
            "accuracy_mode": accuracy_mode,
        },
    })
    return result


@app.get("/api/health")
async def health() -> dict[str, Any]:
    current_service = require_service()
    return {
        "status": "ok",
        "model_ready": True,
        "device": current_service.device,
        "tensorflow_version": current_service.tensorflow_version,
        "warmup_ms": round(current_service.warmup_ms, 1),
        "uptime_seconds": round(time.time() - current_service.started_at, 1),
        "accuracy_mode_default": DEFAULT_TTA,
        "tf_intra_op_threads": current_service.tf_intra_op_threads,
        "tf_inter_op_threads": current_service.tf_inter_op_threads,
        "tta_batching": True,
        "database_ready": DATABASE_PATH.is_file(),
    }


@app.get("/api/config")
async def config() -> dict[str, Any]:
    current_service = require_service()
    return {
        "schema_version": "1.0",
        "emotion_classes": current_service.class_names,
        "visual_state_groups": VISUAL_STATE_GROUPS,
        "visual_state_labels": VISUAL_STATE_LABELS,
        "max_frame_bytes": MAX_FRAME_BYTES,
        "max_frame_dimension": MAX_FRAME_DIMENSION,
        "websocket_path": "/ws/emotion",
    }


@app.post("/api/sessions", status_code=201)
async def store_session(payload: EmotionSessionCreate) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(create_stored_session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/sessions")
async def stored_sessions(
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    sessions = await asyncio.to_thread(list_stored_sessions, limit)
    return {"items": sessions, "count": len(sessions)}


@app.delete("/api/sessions/{session_id}")
async def remove_stored_session(session_id: str) -> dict[str, bool]:
    deleted = await asyncio.to_thread(delete_stored_session, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="找不到工作階段")
    return {"deleted": True}


@app.get("/api/analytics/distribution")
async def analytics_distribution(
    range: Literal["today", "week"] = Query(default="today"),
) -> dict[str, Any]:
    return await asyncio.to_thread(compute_distribution, range)


@app.get("/api/model-eval")
async def model_eval() -> dict[str, Any]:
    try:
        raw = await asyncio.to_thread(MODEL_EVAL_PATH.read_text, "utf-8")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="尚未提供模型評估資料") from exc
    return json.loads(raw)


@app.post("/api/predict")
async def predict_image(
    file: UploadFile = File(...),
    accuracy_mode: bool = Query(DEFAULT_TTA),
) -> dict[str, Any]:
    current_service = require_service()
    data = await file.read(MAX_FRAME_BYTES + 1)
    try:
        frame = decode_frame(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    started = time.perf_counter()
    raw = await asyncio.to_thread(current_service.predict, frame, accuracy_mode)
    elapsed_ms = (time.perf_counter() - started) * 1000
    session = EmotionSession(current_service.class_names)
    return build_response(raw, session, frame, elapsed_ms, accuracy_mode)


def websocket_origin_allowed(websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin")
    return not origin or "*" in ALLOWED_ORIGINS or origin in ALLOWED_ORIGINS


@app.websocket("/ws/emotion")
async def emotion_websocket(websocket: WebSocket) -> None:
    if not websocket_origin_allowed(websocket):
        await websocket.close(code=1008, reason="Origin not allowed")
        return

    await websocket.accept()
    current_service = service
    if current_service is None:
        await websocket.send_json({"type": "error", "message": "模型尚未初始化"})
        await websocket.close(code=1013)
        return

    session = EmotionSession(current_service.class_names)
    accuracy_mode = DEFAULT_TTA
    await websocket.send_json({
        "type": "ready",
        "schema_version": "1.0",
        "device": current_service.device,
        "accuracy_mode": accuracy_mode,
    })

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break

            if message.get("text") is not None:
                try:
                    command = json.loads(message["text"])
                    command_type = command.get("type")
                    if command_type == "reset":
                        session.reset()
                        await websocket.send_json({"type": "reset", "ok": True})
                    elif command_type == "config":
                        accuracy_mode = bool(command.get("accuracy_mode", accuracy_mode))
                        await websocket.send_json({
                            "type": "config",
                            "accuracy_mode": accuracy_mode,
                        })
                    elif command_type == "ping":
                        await websocket.send_json({"type": "pong", "timestamp_ms": int(time.time() * 1000)})
                    else:
                        await websocket.send_json({"type": "error", "message": "未知控制訊息"})
                except (json.JSONDecodeError, TypeError) as exc:
                    await websocket.send_json({"type": "error", "message": f"控制訊息格式錯誤：{exc}"})
                continue

            data = message.get("bytes")
            if data is None:
                await websocket.send_json({"type": "error", "message": "請傳送二進位 JPEG/PNG 影格"})
                continue

            try:
                frame = decode_frame(data)
                started = time.perf_counter()
                raw = await asyncio.to_thread(current_service.predict, frame, accuracy_mode)
                elapsed_ms = (time.perf_counter() - started) * 1000
                response = build_response(raw, session, frame, elapsed_ms, accuracy_mode)
                await websocket.send_json(response)
                pending_event = session.last_completed_visual_state_event
                if pending_event is not None:
                    session.last_completed_visual_state_event = None
                    asyncio.create_task(
                        asyncio.to_thread(persist_visual_state_event, pending_event)
                    )
            except ValueError as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})
            except Exception as exc:
                await websocket.send_json({"type": "error", "message": f"推論失敗：{exc}"})
    except WebSocketDisconnect:
        pass
