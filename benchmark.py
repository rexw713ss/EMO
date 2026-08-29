"""四階段情緒辨識引擎的可重現評估工具。

評估分成兩部分：
1. 分類品質：準確率、誤判率、平均信心度、偵測率與延遲。
2. 時序品質：對同一張影像施加小幅擾動，量測穩定度、切換率、
   機率波動與顯示平滑度。

範例：
    python benchmark.py --samples-per-class 20 --sequence-length 7
    python benchmark.py --stages 3 4 --samples-per-class 5
"""

from __future__ import annotations

import argparse
import gc
import os
import random
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from emotion_system import (
    Stage1_BaselineFER,
    Stage2_FERWithMediaPipe,
    Stage3_FineTuned,
    Stage4_FinalSystem,
)


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TEST_DIR = BASE_DIR / "archive (3)" / "archive (3)" / "Test"
DEFAULT_MODEL_PATH = BASE_DIR / "emotion_model.keras"
DEFAULT_CLASS_NAMES_PATH = BASE_DIR / "class_names.npy"

LABEL_ALIASES = {"angry": "anger"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

STAGE_NAMES = {
    1: "Baseline FER",
    2: "FER + MediaPipe Features",
    3: "Fine-tuned FER",
    4: "Final System",
}


def normalize_label(label: str) -> str:
    """將不同模型的類別命名統一，例如 angry -> anger。"""
    normalized = str(label).strip().lower()
    return LABEL_ALIASES.get(normalized, normalized)


def sample_test_images(
    test_dir: Path,
    samples_per_class: int,
    seed: int,
) -> list[tuple[Path, str]]:
    """以固定亂數種子從每個類別抽取相同上限的影像。"""
    if not test_dir.is_dir():
        raise FileNotFoundError(f"找不到測試資料夾：{test_dir}")

    rng = random.Random(seed)
    sampled: list[tuple[Path, str]] = []

    for class_dir in sorted(path for path in test_dir.iterdir() if path.is_dir()):
        label = normalize_label(class_dir.name)
        images = sorted(
            path for path in class_dir.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        )
        if not images:
            continue

        selected = rng.sample(images, min(samples_per_class, len(images)))
        sampled.extend((path, label) for path in selected)

    if not sampled:
        raise RuntimeError(f"測試資料夾中沒有可用影像：{test_dir}")

    # 固定抽樣後的處理順序，避免類別排列影響時序模型。
    rng.shuffle(sampled)
    return sampled


def make_perturbation_sequence(frame: np.ndarray, length: int) -> list[np.ndarray]:
    """建立可重現的微擾影格序列，模擬攝影機的自然小幅波動。"""
    if length < 1:
        raise ValueError("sequence_length 必須至少為 1")

    h, w = frame.shape[:2]
    operations = (
        lambda image: image.copy(),
        lambda image: cv2.convertScaleAbs(image, alpha=1.04, beta=4),
        lambda image: cv2.warpAffine(
            image,
            np.float32([[1, 0, 2], [0, 1, 1]]),
            (w, h),
            borderMode=cv2.BORDER_REFLECT,
        ),
        lambda image: cv2.GaussianBlur(image, (3, 3), 0),
        lambda image: cv2.convertScaleAbs(image, alpha=0.96, beta=-2),
        lambda image: cv2.warpAffine(
            image,
            np.float32([[1, 0, -2], [0, 1, -1]]),
            (w, h),
            borderMode=cv2.BORDER_REFLECT,
        ),
    )

    # 最後一幀固定回到原圖，所有階段以相同乾淨影像計算分類結果。
    sequence = [operations[index % len(operations)](frame) for index in range(max(0, length - 1))]
    sequence.append(frame.copy())
    return sequence


def reset_temporal_state(stage: Any) -> None:
    """每張測試影像前清空狀態，避免不同人物彼此污染評估。"""
    previous = getattr(stage, "_prev_predictions", None)
    if previous is not None:
        previous.clear()

    nested_stage = getattr(stage, "stage3", None)
    if nested_stage is not None:
        nested_previous = getattr(nested_stage, "_prev_predictions", None)
        if nested_previous is not None:
            nested_previous.clear()

    if not hasattr(stage, "_ema_scores"):
        return

    class_names = list(stage.stage3.class_names)
    stage._ema_scores = {name: 1.0 / len(class_names) for name in class_names}
    stage._emotion_history.clear()
    stage._current_emotion = "neutral"
    stage._current_duration = 0
    stage._transitions.clear()


def result_scores(result: dict[str, Any]) -> dict[str, float]:
    """Stage 4 使用平滑分數，其餘階段使用原始模型分數。"""
    scores = result.get("smoothed_scores") or result.get("all_scores") or {}
    return {normalize_label(key): float(value) for key, value in scores.items()}


def probability_volatility(score_history: list[dict[str, float]]) -> float:
    """計算相鄰影格機率分佈的平均 Total Variation Distance。"""
    if len(score_history) < 2:
        return 0.0

    distances: list[float] = []
    for previous, current in zip(score_history, score_history[1:]):
        labels = set(previous) | set(current)
        distance = 0.5 * sum(abs(previous.get(k, 0.0) - current.get(k, 0.0)) for k in labels)
        distances.append(distance)
    return float(np.mean(distances))


def evaluate_stage(
    stage: Any,
    test_data: Iterable[tuple[Path, str]],
    sequence_length: int,
) -> dict[str, float | int]:
    """在相同影像及擾動序列上計算一個階段的完整指標。"""
    samples = list(test_data)
    correct = 0
    detected = 0
    confidences: list[float] = []
    latencies: list[float] = []
    sequence_stabilities: list[float] = []
    switch_rates: list[float] = []
    probability_volatilities: list[float] = []
    readable_samples = 0
    expected_labels: list[str] = []
    predicted_labels: list[str] = []

    print(f"\n評估 {stage.name}（{len(samples)} 張，每張 {sequence_length} 幀）")
    for index, (image_path, expected) in enumerate(samples, start=1):
        frame = cv2.imread(os.fspath(image_path))
        if frame is None:
            print(f"  [略過] 無法讀取：{image_path}")
            continue
        readable_samples += 1
        expected_labels.append(expected)

        reset_temporal_state(stage)
        predictions: list[str] = []
        score_history: list[dict[str, float]] = []
        final_result: dict[str, Any] | None = None

        for perturbed_frame in make_perturbation_sequence(frame, sequence_length):
            try:
                result = stage.predict(perturbed_frame)
            except Exception as exc:  # 單張壞資料不應中止整份報表
                print(f"  [略過] {image_path.name} 推論失敗：{exc}")
                final_result = None
                break

            final_result = result
            latencies.append(float(result.get("latency_ms", 0.0)))
            prediction = normalize_label(result.get("emotion", "unknown"))
            if prediction != "unknown":
                predictions.append(prediction)
                score_history.append(result_scores(result))

        if final_result is None:
            predicted_labels.append("unknown")
            continue

        final_prediction = normalize_label(final_result.get("emotion", "unknown"))
        predicted_labels.append(final_prediction)
        if final_prediction != "unknown":
            detected += 1
            confidences.append(float(final_result.get("confidence", 0.0)))
            correct += int(final_prediction == expected)

        if predictions:
            dominant_count = Counter(predictions).most_common(1)[0][1]
            sequence_stabilities.append(dominant_count / len(predictions))
            switches = sum(a != b for a, b in zip(predictions, predictions[1:]))
            denominator = max(1, len(predictions) - 1)
            switch_rates.append(switches / denominator)
            probability_volatilities.append(probability_volatility(score_history))

        if index % 20 == 0 or index == len(samples):
            print(f"  已完成 {index}/{len(samples)}")

    evaluated = readable_samples
    # 端到端 accuracy 將漏偵也視為未答對；misclassification 只看已偵測樣本。
    accuracy = correct / evaluated if evaluated else 0.0
    detection_rate = detected / evaluated if evaluated else 0.0
    misclassification_rate = (detected - correct) / detected if detected else 1.0
    mean_latency = float(np.mean(latencies)) if latencies else 0.0
    mean_switch_rate = float(np.mean(switch_rates)) if switch_rates else 0.0
    evaluation_labels = sorted(set(expected_labels))
    macro_f1 = (
        float(
            f1_score(
                expected_labels,
                predicted_labels,
                labels=evaluation_labels,
                average="macro",
                zero_division=0,
            )
        )
        if expected_labels else 0.0
    )

    return {
        "Samples": evaluated,
        "Accuracy": accuracy,
        "Macro F1": macro_f1,
        "Error Rate": 1.0 - accuracy,
        "Misclassification Rate": misclassification_rate,
        "Miss Rate": 1.0 - detection_rate,
        "Mean Confidence": float(np.mean(confidences)) if confidences else 0.0,
        "Detection Rate": detection_rate,
        "Mean Latency (ms)": mean_latency,
        "Inference FPS": 1000.0 / mean_latency if mean_latency > 0 else 0.0,
        "Sequence Stability": float(np.mean(sequence_stabilities)) if sequence_stabilities else 0.0,
        "Prediction Switch Rate": mean_switch_rate,
        "Probability Volatility": (
            float(np.mean(probability_volatilities)) if probability_volatilities else 0.0
        ),
        # 展示流暢度的客觀代理值；越接近 1，畫面標籤越少跳動。
        "Display Smoothness": 1.0 - mean_switch_rate,
    }


def create_stage(
    stage_number: int,
    model_path: Path,
    class_names_path: Path,
    use_tta: bool = False,
) -> Any:
    """依編號建立階段，並在需要時檢查微調模型檔案。"""
    if stage_number == 1:
        return Stage1_BaselineFER()
    if stage_number == 2:
        return Stage2_FERWithMediaPipe()

    if not model_path.is_file():
        raise FileNotFoundError(f"找不到模型檔案：{model_path}")
    if not class_names_path.is_file():
        raise FileNotFoundError(f"找不到類別檔案：{class_names_path}")

    if stage_number == 3:
        return Stage3_FineTuned(
            os.fspath(model_path), os.fspath(class_names_path), use_tta=use_tta
        )
    if stage_number == 4:
        return Stage4_FinalSystem(
            os.fspath(model_path), os.fspath(class_names_path), use_tta=use_tta
        )
    raise ValueError(f"不支援的階段：{stage_number}")


def warm_up_stage(stage: Any, image_path: Path) -> None:
    """先執行一幀，排除 TensorFlow／TFLite／MTCNN 首次呼叫的建圖成本。"""
    frame = cv2.imread(os.fspath(image_path))
    if frame is None:
        return
    try:
        stage.predict(frame)
    finally:
        reset_temporal_state(stage)


def print_comparison(results: dict[str, dict[str, float | int]]) -> None:
    """顯示和企劃表直接對應的改善幅度。"""
    print("\n階段改善摘要")
    print("-" * 60)

    baseline = results.get(STAGE_NAMES[1])
    fine_tuned = results.get(STAGE_NAMES[3])
    final = results.get(STAGE_NAMES[4])

    if baseline and fine_tuned:
        accuracy_gain = float(fine_tuned["Accuracy"]) - float(baseline["Accuracy"])
        volatility_drop = float(baseline["Probability Volatility"]) - float(
            fine_tuned["Probability Volatility"]
        )
        print(f"Fine-tuned vs Baseline 準確率差：{accuracy_gain * 100:+.2f} 個百分點")
        print(f"Fine-tuned vs Baseline 機率波動降低：{volatility_drop:+.4f}")

    if fine_tuned and final:
        switch_drop = float(fine_tuned["Prediction Switch Rate"]) - float(
            final["Prediction Switch Rate"]
        )
        smoothness_gain = float(final["Display Smoothness"]) - float(
            fine_tuned["Display Smoothness"]
        )
        print(f"Final vs Fine-tuned 切換率降低：{switch_drop * 100:+.2f} 個百分點")
        print(f"Final vs Fine-tuned 顯示流暢度：{smoothness_gain * 100:+.2f} 個百分點")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="評估四階段情緒辨識模型")
    parser.add_argument(
        "--stages",
        type=int,
        nargs="+",
        choices=sorted(STAGE_NAMES),
        default=sorted(STAGE_NAMES),
        help="要評估的階段（預設：1 2 3 4）",
    )
    parser.add_argument("--samples-per-class", type=int, default=20, help="每類抽樣張數")
    parser.add_argument("--sequence-length", type=int, default=7, help="每張影像的擾動序列長度")
    parser.add_argument("--seed", type=int, default=42, help="抽樣亂數種子")
    parser.add_argument("--test-dir", type=Path, default=DEFAULT_TEST_DIR)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--class-names", type=Path, default=DEFAULT_CLASS_NAMES_PATH)
    parser.add_argument(
        "--tta",
        action="store_true",
        help="Stage 3/4 啟用水平翻轉測試時增強（較準確但延遲約加倍）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BASE_DIR / "reports" / "engine_benchmark_report.csv",
        help="CSV 報表輸出位置",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.samples_per_class < 1:
        raise SystemExit("--samples-per-class 必須至少為 1")
    if args.sequence_length < 1:
        raise SystemExit("--sequence-length 必須至少為 1")

    test_data = sample_test_images(args.test_dir, args.samples_per_class, args.seed)
    label_counts = Counter(label for _, label in test_data)
    print(f"抽樣完成：{len(test_data)} 張，類別分布 {dict(sorted(label_counts.items()))}")

    results: dict[str, dict[str, float | int]] = {}
    for stage_number in dict.fromkeys(args.stages):
        stage = create_stage(stage_number, args.model, args.class_names, use_tta=args.tta)
        print(f"\n暖機 {stage.name}...")
        warm_up_stage(stage, test_data[0][0])
        results[STAGE_NAMES[stage_number]] = evaluate_stage(
            stage,
            test_data,
            args.sequence_length,
        )
        close = getattr(stage, "close", None)
        if close is not None:
            close()
        del stage
        gc.collect()

    report = pd.DataFrame.from_dict(results, orient="index")
    report.index.name = "Model Version"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, encoding="utf-8-sig", float_format="%.6f")

    print("\n完整評估結果")
    print("=" * 100)
    print(report.to_string(float_format=lambda value: f"{value:.4f}"))
    print_comparison(results)
    print(f"\nCSV 報表：{args.output.resolve()}")


if __name__ == "__main__":
    main()
