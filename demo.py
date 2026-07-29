"""
四階段情緒辨識展示系統 (demo.py)
鍵盤控制：
- 數字鍵 '1'：Stage 1 (Baseline FER)
- 數字鍵 '2'：Stage 2 (FER + MediaPipe)
- 數字鍵 '3'：Stage 3 (Fine-tuned Model)
- 數字鍵 '4'：Stage 4 (Final System)
- 鍵盤 'm'：顯示/隱藏效能儀表板
- 鍵盤 'a'：Stage 3/4 Accuracy Mode（水平翻轉 TTA）
- 鍵盤 'q'：退出系統
"""

import os
import cv2
import numpy as np
import time
from emotion_system import (
    Stage1_BaselineFER,
    Stage2_FERWithMediaPipe,
    Stage3_FineTuned,
    Stage4_FinalSystem
)

# ====== 設定 ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "emotion_model.keras")
CLASS_NAMES_PATH = os.path.join(BASE_DIR, "class_names.npy")

# 顏色對應
EMOTION_COLORS = {
    'happy': (0, 165, 255),     # 橘黃
    'sad': (255, 0, 255),       # 紫色
    'anger': (0, 0, 255),       # 紅色
    'angry': (0, 0, 255),       # 紅色
    'neutral': (255, 255, 0),   # 青色
    'fear': (0, 200, 200),      # 黃綠
    'disgust': (0, 128, 0),     # 綠色
    'surprise': (255, 165, 0),  # 藍橘
    'contempt': (128, 128, 255) # 淺粉紅
}


def draw_header(frame, stage_name, color=(0, 255, 0)):
    """繪製頂部毛玻璃風格標題欄。"""
    h, w = frame.shape[:2]
    # 半透明遮罩
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 55), (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    
    cv2.putText(frame, "Emotion Spectrum Engine", (15, 35),
                cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(frame, stage_name, (w - 320, 35),
                cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)


def draw_dashboard(frame, metrics, show_metrics):
    """繪製側邊效能監控面板。"""
    if not show_metrics:
        return
        
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (w - 250, 60), (w - 10, 350), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    
    y = 90
    cv2.putText(frame, "PERFORMANCE METRICS", (w - 235, y),
                cv2.FONT_HERSHEY_DUPLEX, 0.5, (180, 180, 180), 1)
    
    y += 30
    cv2.putText(frame, f"FPS: {metrics.get('fps', 0.0):.1f}", (w - 235, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    
    y += 25
    cv2.putText(frame, f"Latency: {metrics.get('latency', 0.0):.1f} ms", (w - 235, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
                
    y += 25
    cv2.putText(frame, f"Stability: {metrics.get('stability', 0.0)*100:.0f}%", (w - 235, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
                
    # 畫 MediaPipe 特徵
    features = metrics.get('features', {})
    if features:
        y += 35
        cv2.putText(frame, "FACE FEATURES (AUs)", (w - 235, y),
                    cv2.FONT_HERSHEY_DUPLEX, 0.5, (180, 180, 180), 1)
        
        y += 25
        cv2.putText(frame, f"Smile: {features.get('smile_ratio', 0.0):.2f}", (w - 235, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 255, 200), 1)
        y += 22
        cv2.putText(frame, f"Mouth Open: {features.get('mar', 0.0):.2f}", (w - 235, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 255, 200), 1)
        y += 22
        cv2.putText(frame, f"Brow Raise: {features.get('brow_raise', 0.0):.3f}", (w - 235, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 255, 200), 1)
        y += 22
        cv2.putText(frame, f"Yaw/Pitch: {features.get('yaw', 0.0):.2f}/{features.get('pitch', 0.0):.2f}", (w - 235, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 255, 200), 1)


def draw_trend_bar(frame, trend):
    """在螢幕底部繪製 Stage 4 的情緒波動與趨勢狀態。"""
    if not trend:
        return
        
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - 60), (w, h), (15, 15, 15), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
    
    # 顯示主導情緒
    dominant = trend.get("dominant_emotion", "unknown")
    duration = trend.get("duration_frames", 0)
    color = EMOTION_COLORS.get(dominant, (255, 255, 255))
    
    cv2.putText(frame, f"Current Trend: {dominant.upper()} ({duration} frames)", 
                (15, h - 35), cv2.FONT_HERSHEY_DUPLEX, 0.65, color, 1)
                
    # 繪製歷史情緒流 (簡化版 - 顯示近期情緒轉移)
    transitions = trend.get("recent_transitions", [])
    if transitions:
        trans_str = " -> ".join([t["to"] for t in transitions[-3:]])
        cv2.putText(frame, f"History: {trans_str}", (w - 380, h - 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)


def main():
    print("正在初始化情緒引擎...")
    
    # 初始化四個階段
    stages = {}
    
    # Stage 1 & 2 始終可用
    stages[1] = Stage1_BaselineFER()
    stages[2] = Stage2_FERWithMediaPipe()
    
    # Stage 3 & 4 需要模型存檔
    if os.path.exists(MODEL_PATH) and os.path.exists(CLASS_NAMES_PATH):
        stages[3] = Stage3_FineTuned(MODEL_PATH, CLASS_NAMES_PATH)
        stages[4] = Stage4_FinalSystem(MODEL_PATH, CLASS_NAMES_PATH)
    else:
        print("\n⚠️  [警告] 未檢測到微調模型檔案 (emotion_model.keras)。")
        print("   Stage 3 與 Stage 4 將不可用。請先執行 train_optimized.py 進行訓練。")
        print("   此處先以 Stage 2 取代 Stage 3/4...\n")
        stages[3] = stages[2]
        stages[4] = stages[2]
        
    current_stage = 1
    show_metrics = True
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ 無法開啟攝影機！")
        return
        
    fps_start_time = time.time()
    fps_counter = 0
    fps = 0.0
    
    print("\n系統啟動完成！使用鍵盤切換階段：")
    print("  '1' -> Baseline FER")
    print("  '2' -> FER + MediaPipe Landmarks")
    print("  '3' -> Fine-tuned EfficientNetV2")
    print("  '4' -> Final System (Smoothed + Trend)")
    print("  'a' -> 開關 Accuracy Mode (Stage 3/4，較準確但較慢)")
    print("  'm' -> 開關效能監控面板")
    print("  'q' -> 離開程式")
    
    while True:
        success, frame = cap.read()
        if not success:
            break
            
        frame = cv2.flip(frame, 1)
        engine = stages[current_stage]
        
        # 推理預測
        res = engine.predict(frame)
        
        # 繪製 Bounding Box 和情緒標記
        bbox = res.get("bbox")
        emotion = res.get("emotion", "unknown")
        confidence = res.get("confidence", 0.0)
        
        color = EMOTION_COLORS.get(emotion, (255, 255, 255))
        
        if bbox:
            if current_stage in [3, 4] and len(bbox) == 4:
                # Stage 3 & 4 Bbox 格式可能略有不同 (x, y, w, h)
                x, y, w, h = bbox
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(frame, f"{emotion} ({confidence:.2f})", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            else:
                x, y, w, h = bbox
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(frame, f"{emotion} ({confidence:.2f})", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                            
        # 計算 FPS
        fps_counter += 1
        if (time.time() - fps_start_time) > 1.0:
            fps = fps_counter / (time.time() - fps_start_time)
            fps_counter = 0
            fps_start_time = time.time()
            
        # 準備效能指標
        metrics = {
            "fps": fps,
            "latency": res.get("latency_ms", 0.0),
            "stability": res.get("stability", 0.0),
            "features": res.get("features", {})
        }
        
        # UI 繪製
        draw_header(frame, engine.name, color)
        draw_dashboard(frame, metrics, show_metrics)
        
        if current_stage == 4:
            draw_trend_bar(frame, res.get("trend", {}))
            
        cv2.imshow('Emotion Spectrum Prototype', frame)
        
        # 鍵盤事件監聽
        key = cv2.waitKey(5) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('1'):
            current_stage = 1
            print("切換至 Stage 1: Baseline FER")
        elif key == ord('2'):
            current_stage = 2
            print("切換至 Stage 2: FER + MediaPipe")
        elif key == ord('3'):
            current_stage = 3
            print("切換至 Stage 3: Fine-tuned Model")
        elif key == ord('4'):
            current_stage = 4
            print("切換至 Stage 4: Final System")
        elif key == ord('m'):
            show_metrics = not show_metrics
        elif key == ord('a'):
            engine = stages[current_stage]
            accuracy_engine = engine.stage3 if isinstance(engine, Stage4_FinalSystem) else engine
            if isinstance(accuracy_engine, Stage3_FineTuned):
                accuracy_engine.use_tta = not accuracy_engine.use_tta
                state = "開啟" if accuracy_engine.use_tta else "關閉"
                print(f"Accuracy Mode 已{state}")
            else:
                print("Accuracy Mode 僅適用於 Stage 3/4")
            
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
