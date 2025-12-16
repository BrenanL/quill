# CUDA Setup for Quill

## Current Status

- **GPU Detected:** NVIDIA GeForce RTX 3070 Laptop GPU
- **PyTorch CUDA:** Working (`torch.cuda.is_available() = True`)
- **faster-whisper CUDA:** Not working - missing cuDNN DLLs

## The Problem

When running with `DEVICE = "cuda"` and `COMPUTE_TYPE = "float16"`:

```
Could not locate cudnn_ops64_9.dll. Please make sure it is in your library path!
Invalid handle. Cannot load symbol cudnnCreateTensorDescriptor
```

### Why This Happens

PyTorch bundles its own CUDA/cuDNN libraries internally, but `ctranslate2` (the backend for `faster-whisper`) expects cuDNN to be installed system-wide and available in PATH.

```
┌─────────────────────────────────────┐
│  faster-whisper                     │
├─────────────────────────────────────┤
│  ctranslate2 (C++ inference engine) │
├─────────────────────────────────────┤
│  cuDNN (neural network primitives)  │  ← Missing
├─────────────────────────────────────┤
│  CUDA Runtime                       │  ← Working
├─────────────────────────────────────┤
│  NVIDIA Driver                      │  ← Working
└─────────────────────────────────────┘
```

## TODO: Steps to Enable CUDA

### Option 1: Install cuDNN System-Wide (Recommended)

1. **Check CUDA version:**
   ```powershell
   nvcc --version
   # or
   nvidia-smi
   ```

2. **Download cuDNN:**
   - Go to https://developer.nvidia.com/cudnn (requires free NVIDIA account)
   - Download cuDNN version compatible with your CUDA version
   - For CUDA 12.x, get cuDNN 9.x
   - For CUDA 11.x, get cuDNN 8.x

3. **Install cuDNN:**
   - Extract the downloaded zip
   - Copy contents to CUDA installation directory, OR
   - Add the `bin/` folder to system PATH

4. **Verify installation:**
   ```powershell
   where cudnn_ops64_9.dll
   ```

5. **Update Quill config:**
   ```yaml
   # config.yaml
   transcription:
     device: cuda
     compute_type: float16
   ```

### Option 2: Try int8 on CUDA (May Work Without cuDNN)

Test if `int8` compute type works on CUDA without cuDNN:

```python
# In dictation.py
DEVICE = "cuda"
COMPUTE_TYPE = "int8"
```

This uses different CUDA kernels that may not require cuDNN.

### Option 3: Use ctranslate2 with Bundled CUDA

Some builds of ctranslate2 come with CUDA libraries bundled. Check:

```bash
pip uninstall ctranslate2
pip install ctranslate2 --extra-index-url https://download.pytorch.org/whl/cu121
```

(URL may vary based on CUDA version)

## Testing CUDA

### Test 1: Check ctranslate2 Supported Compute Types

```python
import ctranslate2
print(ctranslate2.get_supported_compute_types('cuda'))
# Expected: ['float16', 'int8_float16', 'int8', 'float32']
```

### Test 2: Basic CUDA Inference

```python
from faster_whisper import WhisperModel
import numpy as np

model = WhisperModel("tiny", device="cuda", compute_type="float16")
audio = np.zeros(16000, dtype=np.float32)  # 1 second silence
segments, info = model.transcribe(audio)
print("CUDA working!")
```

### Test 3: Run Existing GPU Test

```bash
# Update tests/whisper/test_compute_types.py to not skip GPU test
# Then run:
pytest tests/whisper/test_compute_types.py::TestComputeTypes::test_cuda_float16_works -v
```

## Files to Update Once CUDA Works

1. **`config.yaml`** - Set device and compute_type:
   ```yaml
   transcription:
     device: cuda
     compute_type: float16  # or int8_float16
   ```

2. **`src/Quill/dictation.py`** - Either:
   - Make it read from config system, OR
   - Update hardcoded values

3. **`tests/whisper/conftest.py`** - Add GPU fixtures:
   ```python
   @pytest.fixture(scope="session")
   def whisper_model_gpu():
       if not torch.cuda.is_available():
           pytest.skip("CUDA not available")
       return WhisperModel("tiny", device="cuda", compute_type="float16")
   ```

4. **`tests/whisper/test_compute_types.py`** - Fix the skip condition:
   ```python
   @pytest.mark.gpu
   @pytest.mark.skipif(
       not torch.cuda.is_available(),  # Actually check instead of True
       reason="CUDA not available"
   )
   def test_cuda_float16_works(self, tone_audio):
       ...
   ```

## Performance Expectations (Once Working)

| Model  | CPU (int8) | GPU (float16) |
|--------|------------|---------------|
| tiny   | ~0.3-0.5s  | ~0.1s         |
| base   | ~0.8-1.2s  | ~0.2s         |
| small  | ~2-3s      | ~0.3-0.5s     |
| medium | ~8-12s     | ~1-2s         |

(Times for ~5s audio transcription)

## References

- [NVIDIA cuDNN Download](https://developer.nvidia.com/cudnn)
- [ctranslate2 Documentation](https://opennmt.net/CTranslate2/)
- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper)
