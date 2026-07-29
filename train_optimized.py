"""
情緒辨識模型優化訓練腳本 (EfficientNetV2B0 + FER 與自建照片混合訓練)
優化內容：
1. 升級 Backbone 到 EfficientNetV2B0
2. 支援載入並融合 `custom_dataset` 目錄下的自建照片
3. 優化 tf.data pipeline (引入 cache、更正 augment 與 preprocess 順序)
4. 引入 Class Weights 處理類別不平衡
5. 引入 Label Smoothing 0.1 抑制過擬合
6. 調整 Phase 1 學習率至 1e-3 快速收斂分類頭
7. 獨立切分 Validation，Test 不再參與 Early Stopping 或模型選擇
8. 加入旋轉、平移、縮放等攝影機情境資料增強
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.applications import EfficientNetV2B0
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint

# ====== 設定 ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "archive (3)", "archive (3)")
TRAIN_DIR = os.path.join(DATA_DIR, "Train")
TEST_DIR = os.path.join(DATA_DIR, "Test")
LABELS_CSV = os.path.join(DATA_DIR, "labels.csv")
CUSTOM_DIR = os.path.join(BASE_DIR, "custom_dataset")
VALIDATION_DIR = os.path.join(BASE_DIR, "validation_dataset")

IMG_SIZE = 224          # EfficientNetV2B0 輸入大小
BATCH_SIZE = 32
EPOCHS = 30             
LEARNING_RATE_PHASE1 = 1e-3  # 凍結 Base 時較大的學習率
LEARNING_RATE_PHASE2 = 1e-5  # Fine-tuning 學習率
FINE_TUNE_AT = 50           # 解凍後段層數
VALIDATION_SPLIT = 0.15
RANDOM_SEED = 42
CANDIDATE_MODEL_PATH = os.path.join(BASE_DIR, "emotion_model_candidate.keras")
CANDIDATE_CLASS_NAMES_PATH = os.path.join(BASE_DIR, "class_names_candidate.npy")

# 8 類情緒
CLASS_NAMES = sorted(["anger", "contempt", "disgust", "fear", "happy", "neutral", "sad", "surprise"])
NUM_CLASSES = len(CLASS_NAMES)
CLASS_TO_IDX = {name: i for i, name in enumerate(CLASS_NAMES)}


def load_dataset_from_csv(csv_path, base_dir, class_to_idx):
    """從 labels.csv 讀取 FER 標籤。"""
    df = pd.read_csv(csv_path)
    paths = []
    labels = []
    skipped = 0
    
    for _, row in df.iterrows():
        rel_path = row["pth"]
        label = row["label"]
        
        if label not in class_to_idx:
            skipped += 1
            continue
        
        full_path = os.path.join(base_dir, rel_path)
        if os.path.exists(full_path):
            paths.append(full_path)
            labels.append(class_to_idx[label])
        else:
            skipped += 1
            
    print(f"  [FER] 讀取 {len(paths)} 筆資料，跳過 {skipped} 筆")
    return paths, labels


def load_dataset_from_folders(data_dir, class_to_idx, name="Dataset"):
    """從資料夾分類結構讀取圖片（適用於 Test 與 自建照片 custom_dataset）。"""
    paths = []
    labels = []
    
    if not os.path.exists(data_dir):
        print(f"  [{name}] 目錄不存在: {data_dir}，跳過載入")
        return paths, labels
        
    for folder_name in os.listdir(data_dir):
        folder_path = os.path.join(data_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue
        
        label_key = folder_name.lower()
        if label_key not in class_to_idx:
            print(f"  警告: [{name}] 資料夾 '{folder_name}' 無法對應到已知類別，跳過")
            continue
        
        label_idx = class_to_idx[label_key]
        for img_name in os.listdir(folder_path):
            if img_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                paths.append(os.path.join(folder_path, img_name))
                labels.append(label_idx)
                
    print(f"  [{name}] 讀取 {len(paths)} 筆資料")
    return paths, labels


def split_train_validation(paths, labels, validation_split=VALIDATION_SPLIT):
    """依類別分層切分，避免再用最終 Test set 選擇模型。"""
    train_paths, validation_paths, train_labels, validation_labels = train_test_split(
        paths,
        labels,
        test_size=validation_split,
        random_state=RANDOM_SEED,
        stratify=labels,
    )
    return train_paths, train_labels, validation_paths, validation_labels


def create_tf_dataset(paths, labels, is_training=True):
    """建立 tf.data.Dataset；支援 JPEG/PNG 與攝影機情境資料增強。"""
    geometric_augmentation = keras.Sequential([
        layers.RandomRotation(0.03, fill_mode="reflect"),
        layers.RandomTranslation(0.04, 0.04, fill_mode="reflect"),
        layers.RandomZoom(0.05, 0.05, fill_mode="reflect"),
    ])
    
    def parse_image(path, label):
        img = tf.io.read_file(path)
        img = tf.io.decode_image(img, channels=3, expand_animations=False)
        img.set_shape([None, None, 3])
        img = tf.image.resize(img, [IMG_SIZE, IMG_SIZE])
        img = tf.cast(img, tf.float32)
        # 轉換標籤為 one-hot 格式以支援 label_smoothing
        label_oh = tf.one_hot(label, NUM_CLASSES)
        # EfficientNetV2 自帶內建 Rescaling，這裡僅需輸出原像素範圍 [0, 255]
        return img, label_oh
    
    def augment(img, label):
        img = tf.image.random_flip_left_right(img)
        img = tf.image.random_brightness(img, 0.15)
        img = tf.image.random_contrast(img, 0.85, 1.15)
        # 小幅姿態與構圖變化，模擬攝影機前自然移動。
        img = geometric_augmentation(img, training=True)
        img = tf.clip_by_value(img, 0.0, 255.0)
        return img, label
    
    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    
    if is_training:
        ds = ds.shuffle(buffer_size=len(paths), seed=RANDOM_SEED)
    
    ds = ds.map(parse_image, num_parallel_calls=tf.data.AUTOTUNE)
    
    if is_training:
        ds = ds.map(augment, num_parallel_calls=tf.data.AUTOTUNE)
    
    ds = ds.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)
    return ds


def build_model():
    """建立 EfficientNetV2B0 transfer learning 模型與強健分類頭。"""
    base_model = EfficientNetV2B0(
        input_shape=(IMG_SIZE, IMG_SIZE, 3),
        include_top=False,
        weights="imagenet"
    )
    base_model.trainable = False
    
    model = keras.Sequential([
        base_model,
        layers.GlobalAveragePooling2D(),
        layers.BatchNormalization(),
        layers.Dropout(0.4),
        layers.Dense(256, activation="relu"),
        layers.BatchNormalization(),
        layers.Dropout(0.3),
        layers.Dense(NUM_CLASSES, activation="softmax")
    ])
    
    # 使用 CategoricalCrossentropy 搭配標籤平滑化
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LEARNING_RATE_PHASE1),
        loss=tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1),
        metrics=["accuracy"]
    )
    
    return model, base_model


def fine_tune_model(model, base_model):
    """解凍後段層數進行 Fine-tuning。"""
    base_model.trainable = True
    
    # 僅解凍後段特定層數，前方層數保持凍結
    for layer in base_model.layers[:-FINE_TUNE_AT]:
        layer.trainable = False
        
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LEARNING_RATE_PHASE2),
        loss=tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1),
        metrics=["accuracy"]
    )
    return model


def evaluate_and_report(model, test_ds, test_labels, save_dir, artifact_prefix="candidate_"):
    """評估並繪製混淆矩陣。"""
    y_pred_probs = model.predict(test_ds)
    y_pred = np.argmax(y_pred_probs, axis=1)
    y_true = np.array(test_labels)
    
    report = classification_report(y_true, y_pred, target_names=CLASS_NAMES, digits=4)
    print("\n" + "=" * 60)
    print("Classification Report (Optimized Model):")
    print("=" * 60)
    print(report)
    
    report_path = os.path.join(save_dir, f"{artifact_prefix}classification_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    # 混淆矩陣
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(10, 8))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=CLASS_NAMES)
    disp.plot(ax=ax, cmap="Blues", values_format="d")
    plt.title("Emotion Classification - Confusion Matrix (Optimized)")
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, f"{artifact_prefix}confusion_matrix.png"), dpi=150)
    plt.close()
    
    return report


def main():
    print("=" * 60)
    print("情緒辨識優化訓練 - EfficientNetV2B0 + 雙資料集融合")
    print("=" * 60)
    
    # GPU 偵測
    gpus = tf.config.list_physical_devices("GPU")
    if gpus:
        print(f"偵測到 GPU: {gpus}")
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    else:
        print("未偵測到 GPU，使用 CPU 進行訓練")
        
    # ===== 載入資料 =====
    print("\n[1/5] 載入資料集...")
    
    # 1. 載入 FER 訓練集
    fer_paths, fer_labels = load_dataset_from_csv(LABELS_CSV, TRAIN_DIR, CLASS_TO_IDX)
    
    # 2. 載入自建照片集
    custom_paths, custom_labels = load_dataset_from_folders(CUSTOM_DIR, CLASS_TO_IDX, name="Custom")
    
    # 融合資料；Validation 優先使用獨立資料夾，否則從訓練資料分層切出。
    all_train_paths = fer_paths + custom_paths
    all_train_labels = fer_labels + custom_labels
    validation_paths, validation_labels = load_dataset_from_folders(
        VALIDATION_DIR, CLASS_TO_IDX, name="Validation"
    )
    if validation_paths:
        train_paths, train_labels = all_train_paths, all_train_labels
        print("  使用獨立 validation_dataset；請確保人物不與 Train/Test 重複")
    else:
        train_paths, train_labels, validation_paths, validation_labels = split_train_validation(
            all_train_paths, all_train_labels
        )
        print(
            f"  未提供獨立 validation_dataset，已按類別分層切分 "
            f"{VALIDATION_SPLIT:.0%} 作為 Validation"
        )
        if custom_paths:
            print("  [提醒] 影片抽幀資料應按受試者切分，避免同一人跨 Train/Validation")
    
    # 3. 載入測試集
    test_paths, test_labels = load_dataset_from_folders(TEST_DIR, CLASS_TO_IDX, name="Test")
    
    print(
        f"\n原始訓練資料: {len(all_train_labels)} "
        f"(FER: {len(fer_labels)}, Custom: {len(custom_labels)})"
    )
    print(f"實際 Train: {len(train_labels)}")
    print(f"Validation: {len(validation_labels)}")
    print(f"測試集總計: {len(test_labels)}")
    if not custom_paths:
        print("[提醒] custom_dataset 目前沒有影像，模型尚未進行展示場域適應")
    
    # 計算 Class Weights 處理類別不平衡
    class_weights = compute_class_weight(
        class_weight='balanced',
        classes=np.unique(train_labels),
        y=np.array(train_labels)
    )
    class_weight_dict = dict(zip(np.unique(train_labels), class_weights))
    print("\n自適應 Class Weights 權重:")
    for cls_name in CLASS_NAMES:
        idx = CLASS_TO_IDX[cls_name]
        weight = class_weight_dict.get(idx, 1.0)
        count = sum(1 for l in train_labels if l == idx)
        print(f"  {cls_name}: {count} 筆 (權重: {weight:.4f})")
        
    # 建立 Dataset
    train_ds = create_tf_dataset(train_paths, train_labels, is_training=True)
    validation_ds = create_tf_dataset(validation_paths, validation_labels, is_training=False)
    test_ds = create_tf_dataset(test_paths, test_labels, is_training=False)
    
    # ===== Phase 1: 訓練分類頭 =====
    print("\n[2/5] Phase 1: 訓練分類頭 (學習率: 1e-3, base model 凍結)...")
    model, base_model = build_model()
    model.summary()
    
    callbacks_p1 = [
        EarlyStopping(monitor="val_accuracy", patience=5, restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, verbose=1)
    ]
    
    history1 = model.fit(
        train_ds,
        validation_data=validation_ds,
        epochs=EPOCHS,
        class_weight=class_weight_dict,
        callbacks=callbacks_p1,
        verbose=1
    )
    
    phase1_acc = max(history1.history["val_accuracy"])
    print(f"\nPhase 1 最佳驗證 Accuracy: {phase1_acc:.4f}")
    
    # ===== Phase 2: Fine-tune =====
    print("\n[3/5] Phase 2: Fine-tuning (學習率: 1e-5, 解凍後 50 層)...")
    model = fine_tune_model(model, base_model)
    
    callbacks_p2 = [
        EarlyStopping(monitor="val_accuracy", patience=5, restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, verbose=1),
        ModelCheckpoint(
            CANDIDATE_MODEL_PATH,
            monitor="val_accuracy",
            save_best_only=True,
            verbose=1
        )
    ]
    
    history2 = model.fit(
        train_ds,
        validation_data=validation_ds,
        epochs=EPOCHS,
        class_weight=class_weight_dict,
        callbacks=callbacks_p2,
        verbose=1
    )
    
    phase2_acc = max(history2.history["val_accuracy"])
    print(f"\nPhase 2 最佳驗證 Accuracy: {phase2_acc:.4f}")
    
    # ===== 評估與輸出結果 =====
    print("\n[4/5] 測試集評估與產生報告...")
    evaluate_and_report(model, test_ds, test_labels, BASE_DIR)
    
    # 儲存類別
    np.save(CANDIDATE_CLASS_NAMES_PATH, CLASS_NAMES)
    
    # 繪製曲線
    print("\n[5/5] 繪製並儲存訓練曲線...")
    all_acc = history1.history["accuracy"] + history2.history["accuracy"]
    all_val_acc = history1.history["val_accuracy"] + history2.history["val_accuracy"]
    all_loss = history1.history["loss"] + history2.history["loss"]
    all_val_loss = history1.history["val_loss"] + history2.history["val_loss"]
    phase1_epochs = len(history1.history["accuracy"])
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    ax1.plot(all_acc, label="Train Accuracy")
    ax1.plot(all_val_acc, label="Val Accuracy")
    ax1.axvline(x=phase1_epochs, color="r", linestyle="--", alpha=0.5, label="Fine-tune Start")
    ax1.set_title("Accuracy")
    ax1.set_xlabel("Epoch")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    ax2.plot(all_loss, label="Train Loss")
    ax2.plot(all_val_loss, label="Val Loss")
    ax2.axvline(x=phase1_epochs, color="r", linestyle="--", alpha=0.5, label="Fine-tune Start")
    ax2.set_title("Loss")
    ax2.set_xlabel("Epoch")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    candidate_history_path = os.path.join(BASE_DIR, "candidate_training_history.png")
    plt.savefig(candidate_history_path, dpi=150)
    plt.close()
    
    print("\n" + "=" * 60)
    print("優化版訓練完成！")
    print(f"  候選模型: {CANDIDATE_MODEL_PATH}")
    print(f"  候選類別: {CANDIDATE_CLASS_NAMES_PATH}")
    print(f"  訓練曲線: {candidate_history_path}")
    print(f"  混淆矩陣: {os.path.join(BASE_DIR, 'candidate_confusion_matrix.png')}")
    print("  正式 emotion_model.keras 不會自動覆蓋；請先執行同條件 benchmark")
    print("=" * 60)


if __name__ == "__main__":
    main()
