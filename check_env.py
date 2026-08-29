"""Quick environment check."""
import subprocess
import sys
print("Python:", sys.version)
print("Python path:", sys.executable)

checks = [
    ("tensorflow", "tf"),
    ("pandas", "pd"),
    ("sklearn", "sklearn"),
    ("matplotlib", "mpl"),
    ("cv2", "cv2"),
    ("mediapipe", "mp"),
    ("numpy", "np"),
]

for mod_name, alias in checks:
    try:
        m = __import__(mod_name)
        ver = getattr(m, "__version__", "ok")
        print(f"  {mod_name}: {ver}")
    except ImportError:
        print(f"  {mod_name}: NOT INSTALLED")

tensorflow_cuda_build = None
try:
    import tensorflow as tf
    gpus = tf.config.list_physical_devices("GPU")
    tensorflow_cuda_build = tf.test.is_built_with_cuda()
    print(f"\nTensorFlow CUDA build: {tensorflow_cuda_build}")
    print(f"TensorFlow GPU: {gpus if gpus else 'None (this Python environment uses CPU)'}")
except Exception as exc:
    print(f"\nTensorFlow GPU check failed: {exc}")

try:
    output = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()
    print(f"NVIDIA hardware: {output}")
except (FileNotFoundError, subprocess.CalledProcessError) as exc:
    print(f"NVIDIA hardware check unavailable: {exc}")

if sys.platform == "win32" and tensorflow_cuda_build is False:
    print("Note: TensorFlow >= 2.11 on native Windows is CPU-only; use the GPU Docker/WSL2 setup.")
