"""
=============================================================
  BUỜC 2: TRAINING MODEL AI NHẬN DIỆN TRANG PHỤC
  uniform_trainer.py

  Sử dụng Transfer Learning với MobileNetV2 (của Google)
  Model nhẹ, chạy được tốt trên Raspberry Pi 4

  PHÂN LOẠI 2 NHÃN:
    - trang_phuc_dan_toc : Trang phục dân tộc (Đúng vào Thứ 2)
    - other             : Không phải dân tộc → UNCLEAR → Camera chụp

  CHẠY LỆNH: python uniform_trainer.py
  OUTPUT   : data/uniform_model_v2.tflite  (dùng trên Raspberry Pi)
             data/uniform_model_v2.h5      (backup, dùng để train thêm)
             data/uniform_labels_v2.json   (nhãn tương ứng)
=============================================================
"""

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"  # Tắt log thừa của TensorFlow

import json
import numpy as np
from pathlib import Path

# ==================== CẤU HÌNH ====================
BASE_DIR        = Path(__file__).parent
_CANDIDATES = [
    BASE_DIR.parents[1] / "backend" / "data",
    BASE_DIR.parent / "data",
    BASE_DIR / "data",
    BASE_DIR.parents[1] / "data",
]
DATA_DIR        = next((d for d in _CANDIDATES if (d / "uniform_dataset_v2").exists()), BASE_DIR / "data")
DATASET_DIR     = DATA_DIR / "uniform_dataset_v2"   # Dataset mới 2 nhãn
MODEL_H5_PATH   = DATA_DIR / "uniform_model_v2.h5"
MODEL_TFLITE    = DATA_DIR / "uniform_model_v2.tflite"
LABELS_PATH     = DATA_DIR / "uniform_labels_v2.json"

IMAGE_SIZE      = (224, 224)
BATCH_SIZE      = 16   # Giảm xuống 16 nếu RAM máy tính thấp
EPOCHS_FROZEN   = 15   # Epoch giai đoạn 1: chỉ train lớp đầu ra
EPOCHS_FINETUNE = 10   # Epoch giai đoạn 2: fine-tune toàn bộ
LEARNING_RATE   = 1e-3
FINE_TUNE_LR    = 1e-5


def check_dataset():
    """Kiểm tra dataset trước khi training."""
    train_dir = DATASET_DIR / "train"
    if not train_dir.exists():
        print("[ERROR] Chưa có dataset! Hãy chạy: python step1_data_prep_v2.py")
        return None, None
    
    classes = sorted([d.name for d in train_dir.iterdir() if d.is_dir()])
    if len(classes) == 0:
        print("[ERROR] Không tìm thấy nhãn nào trong dataset/train/")
        return None, None
    
    # Kiểm tra các nhãn bắt buộc
    REQUIRED = {"trang_phuc_dan_toc", "other"}
    missing  = REQUIRED - set(classes)
    if missing:
        print(f"[WARN] Thiếu nhãn: {missing}")
        print(f"       Hãy chạy lại: python step1_data_prep_v2.py")
    else:
        print(f"[OK] Model sẻ phân loại 2 nhãn: 'trang_phuc_dan_toc' và 'other'")
        print(f"     'other' → UNCLEAR → Camera chụp + upload cloud")

    print(f"[INFO] Tìm thấy {len(classes)} nhãn: {classes}")
    return classes, len(classes)


def build_model(num_classes: int):
    """Xây dựng model MobileNetV2 với Transfer Learning."""
    import tensorflow as tf
    from tensorflow.keras.applications import MobileNetV2
    from tensorflow.keras import layers, models

    # Load model MobileNetV2 đã được train sẵn trên ImageNet
    # (1.4 triệu ảnh - 1000 loại vật thể)
    base_model = MobileNetV2(
        input_shape=(*IMAGE_SIZE, 3),
        include_top=False,      # Bỏ lớp phân loại cũ
        weights="imagenet"      # Giữ lại kiến thức về nhận diện hình ảnh
    )
    # Giai đoạn 1: Đóng băng base model, chỉ train lớp đầu ra
    base_model.trainable = False

    # Thêm lớp phân loại riêng cho bài toán trang phục
    inputs  = tf.keras.Input(shape=(*IMAGE_SIZE, 3))
    x       = base_model(inputs, training=False)
    x       = layers.GlobalAveragePooling2D()(x)
    x       = layers.Dense(256, activation="relu")(x)
    x       = layers.Dropout(0.4)(x)             # Chống overfitting
    x       = layers.Dense(128, activation="relu")(x)
    x       = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)

    model = tf.keras.Model(inputs, outputs)
    return model, base_model


def create_data_generators():
    """Tạo data generator với augmentation để tăng cường dữ liệu."""
    from tensorflow.keras.preprocessing.image import ImageDataGenerator

    # Augmentation cho training: tạo thêm nhiều biến thể ảnh từ dataset ít
    train_datagen = ImageDataGenerator(
        rescale           = 1.0 / 255,
        rotation_range    = 20,          # Xoay ảnh ngẫu nhiên ±20 độ
        width_shift_range = 0.15,        # Dịch ngang
        height_shift_range= 0.15,        # Dịch dọc
        horizontal_flip   = True,        # Lật ngang (trang phục nhìn từ 2 phía)
        brightness_range  = [0.7, 1.3],  # Giả lập ánh sáng buổi sáng sớm / trưa
        zoom_range        = 0.15,        # Zoom in/out (camera gần/xa)
        shear_range       = 0.1,
        fill_mode         = "nearest"
    )

    # Validation: chỉ normalize, KHÔNG augment
    val_datagen = ImageDataGenerator(rescale=1.0 / 255)

    train_gen = train_datagen.flow_from_directory(
        DATASET_DIR / "train",
        target_size  = IMAGE_SIZE,
        batch_size   = BATCH_SIZE,
        class_mode   = "categorical",
        shuffle      = True
    )

    val_gen = val_datagen.flow_from_directory(
        DATASET_DIR / "val",
        target_size  = IMAGE_SIZE,
        batch_size   = BATCH_SIZE,
        class_mode   = "categorical",
        shuffle      = False
    )

    return train_gen, val_gen


def train():
    import tensorflow as tf

    print("=" * 60)
    print("  TRAINING MODEL NHẬN DIỆN TRANG PHỤC HỌC SINH (v2)")
    print("  Nhãn: [trang_phuc_dan_toc] vs [other]")
    print("=" * 60)
    
    # Kiểm tra GPU
    gpus = tf.config.list_physical_devices("GPU")
    if gpus:
        print(f"[INFO] Phát hiện GPU: {gpus[0].name} - Training sẻ nhanh hơn nhiều!")
    else:
        print("[INFO] Không có GPU - Training bằng CPU (chậm hơn, nhưng vẫn OK)")

    # Kiểm tra dataset
    classes, num_classes = check_dataset()
    if classes is None:
        return

    # Lưu labels
    LABELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LABELS_PATH, "w", encoding="utf-8") as f:
        json.dump(classes, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Đã lưu nhãn vào: {LABELS_PATH}")

    # Tạo data generators
    train_gen, val_gen = create_data_generators()
    print(f"[INFO] Train: {train_gen.samples} ảnh | Val: {val_gen.samples} ảnh")

    # ── Tính class_weight để xử lý mất cân bằng nhãn ──
    # Ví dụ: dan_toc=645 ảnh, other=105 ảnh
    # → class_weight sẻ tăng trọng số nhãn ít ảnh (other)
    from sklearn.utils.class_weight import compute_class_weight
    try:
        y_train = train_gen.classes
        class_weights_arr = compute_class_weight(
            class_weight="balanced",
            classes=np.unique(y_train),
            y=y_train
        )
        class_weight_dict = dict(enumerate(class_weights_arr))
        print(f"[INFO] class_weight: {class_weight_dict}")
        print(f"       (Nhãn ít ảnh sẽ có trọng số cao hơn → bù mất cân bằng)")
    except Exception as e:
        print(f"[WARN] Không tính được class_weight ({e}) — dùng None")
        class_weight_dict = None

    # Xây dựng model
    model, base_model = build_model(num_classes)

    # ==================== GIAI ĐOẠN 1: TRAIN LỚP ĐẦU RA ====================
    print(f"\n[PHASE 1] Training lớp đầu ra ({EPOCHS_FROZEN} epochs)...")
    model.compile(
        optimizer = tf.keras.optimizers.Adam(learning_rate=LEARNING_RATE),
        loss      = "categorical_crossentropy",
        metrics   = ["accuracy"]
    )

    callbacks_phase1 = [
        tf.keras.callbacks.ModelCheckpoint(
            str(MODEL_H5_PATH),
            save_best_only = True,
            monitor        = "val_accuracy",
            verbose        = 1
        ),
        tf.keras.callbacks.EarlyStopping(
            patience = 8,
            monitor  = "val_accuracy",
            restore_best_weights = True,
            verbose  = 1
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor  = "val_loss",
            factor   = 0.5,
            patience = 3,
            verbose  = 1
        )
    ]

    history1 = model.fit(
        train_gen,
        validation_data = val_gen,
        epochs          = EPOCHS_FROZEN,
        callbacks       = callbacks_phase1,
        class_weight    = class_weight_dict,   # Bù mất cân bằng
        verbose         = 1
    )

    best_acc_phase1 = max(history1.history.get("val_accuracy", [0]))
    print(f"\n[PHASE 1] Hoàn thành! Val accuracy tốt nhất: {best_acc_phase1*100:.1f}%")

    # ==================== GIAI ĐOẠN 2: FINE-TUNE TOÀN BỘ ====================
    print(f"\n[PHASE 2] Fine-tuning toàn bộ model ({EPOCHS_FINETUNE} epochs)...")
    # Mở khóa base model để train thêm (học các đặc trưng tinh tế hơn)
    base_model.trainable = True
    
    # Chỉ fine-tune từ lớp thứ 100 trở đi (giữ nguyên các lớp thấp)
    for layer in base_model.layers[:100]:
        layer.trainable = False

    model.compile(
        optimizer = tf.keras.optimizers.Adam(learning_rate=FINE_TUNE_LR),
        loss      = "categorical_crossentropy",
        metrics   = ["accuracy"]
    )

    callbacks_phase2 = [
        tf.keras.callbacks.ModelCheckpoint(
            str(MODEL_H5_PATH),
            save_best_only = True,
            monitor        = "val_accuracy",
            verbose        = 1
        ),
        tf.keras.callbacks.EarlyStopping(
            patience = 6,
            monitor  = "val_accuracy",
            restore_best_weights = True,
            verbose  = 1
        )
    ]

    history2 = model.fit(
        train_gen,
        validation_data = val_gen,
        epochs          = EPOCHS_FINETUNE,
        callbacks       = callbacks_phase2,
        class_weight    = class_weight_dict,   # Bù mất cân bằng
        verbose         = 1
    )

    best_acc_phase2 = max(history2.history.get("val_accuracy", [0]))
    best_acc_overall = max(best_acc_phase1, best_acc_phase2)
    print(f"\n[PHASE 2] Hoàn thành! Val accuracy tốt nhất: {best_acc_phase2*100:.1f}%")

    # ==================== XUẤT FILE TFLITE ====================
    print("\n[EXPORT] Đang xuất file TFLite cho Raspberry Pi...")
    
    # Load model tốt nhất đã lưu
    best_model = tf.keras.models.load_model(str(MODEL_H5_PATH))
    
    # Chuyển đổi sang TFLite với tối ưu hóa kích thước
    converter = tf.lite.TFLiteConverter.from_keras_model(best_model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()
    
    with open(MODEL_TFLITE, "wb") as f:
        f.write(tflite_model)
    
    tflite_size = MODEL_TFLITE.stat().st_size / (1024 * 1024)

    print("\n" + "=" * 60)
    print("  TRAINING HOÀN THÀNH!")
    print("=" * 60)
    print(f"  Độ chính xác cuối cùng : {best_acc_overall*100:.1f}%")
    print(f"  Nhãn phân loại      : {classes}")
    print(f"  Model H5 (backup)      : {MODEL_H5_PATH}")
    print(f"  Model TFLite (Pi4)     : {MODEL_TFLITE} ({tflite_size:.1f} MB)")
    print(f"  File nhãn              : {LABELS_PATH}")
    print("=" * 60)

    # [fix] Canh bao do tin cay khi tap validation qua nho — dac biet
    # quan trong khi do chinh xac bao cao gan 100% (dau hieu kinh dien
    # cua overfitting / tap val khong du dai dien, KHONG phai model
    # "hoan hao").
    MIN_RELIABLE_VAL_SAMPLES = 100
    if val_gen.samples < MIN_RELIABLE_VAL_SAMPLES:
        print("\n  ⚠️  CẢNH BÁO ĐỘ TIN CẬY:")
        print(f"     Tập validation chỉ có {val_gen.samples} ảnh"
              f" (khuyến nghị tối thiểu {MIN_RELIABLE_VAL_SAMPLES}+).")
        if best_acc_overall >= 0.97:
            print(f"     Độ chính xác {best_acc_overall*100:.1f}% với tập val nhỏ như vậy")
            print("     RẤT CÓ THỂ là dấu hiệu overfitting hoặc tập val chưa đại diện")
            print("     đủ tình huống thực tế (góc quay, ánh sáng, nền khác nhau),")
            print("     KHÔNG nên xem đây là độ chính xác thực tế khi triển khai.")
        print("     → Nên thu thập thêm ảnh thực tế (đặc biệt nhãn ít ảnh)")
        print("       trước khi tin tưởng triển khai model này diện rộng.")

    print("\n[NEXT] Cập nhật MODEL_PATH trong uniform_checker.py:")
    print(f"       MODEL_PATH = '{MODEL_TFLITE}'")
    print(f"       LABELS_PATH = '{LABELS_PATH}'")
    print("\n[NEXT] Chạy bước tiếp theo: python uniform_checker.py --test")


if __name__ == "__main__":
    train()
