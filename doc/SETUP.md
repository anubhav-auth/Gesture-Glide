# GestureGlide Setup & Installation Guide

## Quick Start

### 1. System Requirements

**Minimum Requirements:**
- Python 3.8 or higher
- 4GB RAM
- Webcam (720p, 30fps recommended)
- Windows, macOS, or Linux

**Recommended Requirements:**
- Python 3.10+
- 8GB+ RAM
- GPU support (NVIDIA with CUDA, or Apple Silicon)
- 1080p+ webcam with 60fps capability

### 2. Installation Steps

#### Step 1: Clone or Download the Repository
```bash
git clone https://github.com/yourusername/gestureglide.git
cd gestureglide
```

#### Step 2: Create Virtual Environment
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 4: Verify Installation
```bash
python -c "import cv2, mediapipe, pyautogui; print('✓ All dependencies installed')"
```

### 3. Running GestureGlide

**Basic Usage:**
```bash
cd gestureglide
python main.py
```

**With Custom Configuration:**
```bash
python main.py --config custom_config.yaml
```

**Run Calibration:**
```bash
python scripts/calibrate.py
```

**Performance Benchmark:**
```bash
python scripts/benchmark.py
```

**Interactive Gesture Test:**
```bash
python scripts/test_gestures.py
```

### 4. First Launch Checklist

1. **Lighting**: Ensure adequate lighting (natural or artificial)
2. **Background**: Use a plain background for best hand detection
3. **Webcam**: Test webcam in system settings before launching
4. **Space**: Clear area in front of webcam (about 1 meter)
5. **Calibration**: Run calibration if prompted on first launch
6. **Config**: Review `config.yaml` for preferred settings

## Platform-Specific Instructions

### Windows Installation

**Additional Dependencies (Optional):**
```bash
# For GPU support with CUDA
pip install tensorflow[and-cuda]
```

**Audio/Visual Issues:**
- Check Windows Settings > Privacy > Camera permissions
- Allow Python in Windows Defender Firewall

**Running at Startup:**
```powershell
# Create shortcut to venv\Scripts\python.exe
# Add target: `<path>\python.exe main.py`
```

### macOS Installation

**Camera Permissions:**
1. Go to System Preferences > Security & Privacy > Camera
2. Add Terminal (or your IDE) to allowed apps
3. Restart the application

**M1/M2 Silicon Optimization:**
```bash
# Install native versions for best performance
pip install --upgrade --force-reinstall \
  --no-binary :all: numpy scipy opencv-python
```

**Running with GPU:**
- Apple Neural Engine (ANE) is automatically used when available

### Linux Installation

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install python3-dev python3-pip
sudo apt-get install libsm6 libxext6 libxrender-dev
pip install -r requirements.txt
```

**Fedora/RHEL:**
```bash
sudo dnf install python3-devel opencv-devel
pip install -r requirements.txt
```

**Camera Permissions:**
```bash
sudo usermod -a -G video $USER
# Log out and back in for changes to take effect
```

## Troubleshooting Installation

### Issue: "ModuleNotFoundError: No module named 'cv2'"
```bash
# Solution: Reinstall OpenCV
pip uninstall opencv-python
pip install opencv-python==4.8.1.78
```

### Issue: "ImportError: libGL.so.1"
```bash
# Solution (Linux): Install missing libraries
sudo apt-get install libgl1-mesa-glx
```

### Issue: "PyAutoGUI cannot find cursor"
```bash
# Solution: Requires display environment
# On headless systems, use Xvfb
sudo apt-get install xvfb
xvfb-run python main.py
```

### Issue: Webcam not detected
```bash
# Solution: Check available cameras
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
# Try different camera indices (0, 1, 2...)
```

## Configuration

### Basic Configuration
1. Edit `config.yaml` in the project root
2. Adjust detection confidence, thresholds, visualization options
3. Settings take effect on next application restart

### Common Configuration Changes

**Increase Cursor Speed:**
```yaml
cursor_control:
  speed_multiplier: 1.5  # Default is 1.0
```

**Adjust Gesture Sensitivity:**
```yaml
gesture_detection:
  pinch_threshold_min: 1.5  # More sensitive (lower value)
  pinch_threshold_max: 2.5
```

**Enable GPU Acceleration:**
```yaml
performance:
  use_gpu: true
```

**Power Saving Mode:**
```yaml
performance:
  power_saving_mode: true
  target_fps: 15
```

## Next Steps

1. **Run Calibration**: `python scripts/calibrate.py`
2. **Read Documentation**: See `MAINTENANCE.md` for day-to-day usage
3. **Learn Gestures**: See `GESTURE_MAPPING.md` for gesture definitions
4. **Tune Performance**: See `PERFORMANCE_TUNING.md` for optimization

## Getting Help

- Check `TROUBLESHOOTING.md` for common issues
- Review `MAINTENANCE.md` for operation guidelines
- See `docs/ARCHITECTURE.md` for technical details
- Check project repository issues/discussions
