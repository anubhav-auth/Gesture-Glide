# GestureGlide Maintenance & Operation Guide

## Daily Operation

### Starting GestureGlide

1. **Activate Virtual Environment**
   ```bash
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

2. **Launch Application**
   ```bash
   python main.py
   ```

3. **Visual Feedback**
   - Green hand skeleton overlay shows detected hands
   - Gesture indicators display recognized gestures
   - FPS counter shows performance (if enabled in config)

### Stopping GestureGlide

- Press **ESC** key to exit gracefully
- Or use **Ctrl+C** in terminal (force quit)

## Common Issues & Solutions

### Issue: Hand Not Detected

**Symptoms:** No hand skeleton appears on screen, gestures don't work

**Diagnosis:**
1. Check lighting in your environment
2. Verify hand is within 30-50cm of webcam
3. Ensure hand is clearly visible (not partially occluded)
4. Check webcam focus and cleanliness

**Solutions:**
```yaml
# Make detection more sensitive in config.yaml
hand_tracking:
  detection_confidence: 0.5  # Lower value = more sensitive
  model_complexity: 1        # Use full model for better accuracy
```

### Issue: Jittery/Unstable Cursor

**Symptoms:** Cursor jumps around or is very shaky

**Solutions:**
1. Increase Kalman filter smoothing:
   ```yaml
   cursor_control:
     kalman_process_noise: 0.005  # Lower = more smoothing
   ```

2. Switch to moving average filter:
   ```yaml
   cursor_control:
     smoothing_filter: "moving_average"
     moving_average_window: 10  # Higher = more smoothing
   ```

3. Verify webcam is stable (not moving)

### Issue: Clicks Triggering Randomly

**Symptoms:** Random clicks occur during normal hand movement

**Solutions:**
```yaml
# Increase debounce time
gesture_detection:
  click_debounce_ms: 150    # Default is 100
  pinch_threshold_min: 2.2  # Make thresholds tighter
  pinch_threshold_max: 2.8
```

### Issue: Drag Operations Not Working

**Symptoms:** Pinch hold doesn't initiate drag, or drag ends prematurely

**Solutions:**
```yaml
gesture_detection:
  drag_hold_threshold_ms: 250  # Increase hold time
  drag_debounce_ms: 30         # Reduce debounce during drag
  use_hysteresis: true         # Enable hysteresis
```

### Issue: High CPU Usage / Performance Lag

**Symptoms:** Constant 90-100% CPU usage, cursor movement laggy

**Solutions - Try in order:**

1. Enable power saving mode:
   ```yaml
   performance:
     power_saving_mode: true
     target_fps: 15
   ```

2. Reduce processing scale:
   ```yaml
   performance:
     processing_scale: 0.75  # Process at 75% resolution
   ```

3. Increase frame skip:
   ```yaml
   performance:
     frame_skip: 2  # Process every other frame
   ```

4. Enable GPU acceleration (if available):
   ```yaml
   performance:
     use_gpu: true
   ```

5. Disable unnecessary visualizations:
   ```yaml
   visualization:
     show_hand_skeleton: false
     show_landmarks: false
     show_gesture_indicators: false
   ```

### Issue: Gestures Not Recognized Consistently

**Symptoms:** Same gesture sometimes works, sometimes doesn't

**Solutions:**
1. Run calibration: `python scripts/calibrate.py`
2. Increase gesture hold time:
   ```yaml
   gesture_detection:
     click_debounce_ms: 120
     drag_hold_threshold_ms: 250
   ```
3. Verify adequate lighting
4. Adjust thresholds based on your hand size:
   ```yaml
   gesture_detection:
     pinch_threshold_min: 1.8  # For smaller hands
     pinch_threshold_max: 3.2
   ```

## Performance Monitoring

### Check Current Performance

```bash
python scripts/benchmark.py
```

This provides:
- Average FPS
- Processing latency (ms)
- CPU usage (%)
- Memory usage (MB)

### Logging

Enable logging to monitor system behavior:

```yaml
system:
  log_level: "INFO"
  log_file: "gestureglide.log"
  debug_mode: false
```

View logs:
```bash
tail -f gestureglide.log  # macOS/Linux
type gestureglide.log     # Windows
```

### Real-time Performance Display

Enable FPS and latency overlay:
```yaml
visualization:
  show_performance_metrics: true
```

## Calibration

### When to Calibrate

- First launch
- After adjusting thresholds
- When moving to new location
- After hardware changes (new webcam)
- If gesture accuracy decreases

### Running Calibration

```bash
python scripts/calibrate.py
```

Calibration process:
1. Positions 9 points on screen
2. Move hand to each point
3. Performs pinch at each position
4. Analyzes gesture variance
5. Saves calibration profile to `data/calibration_profile.json`

### Manual Calibration Adjustment

Edit `config.yaml` directly for fine-tuning:

```yaml
gesture_detection:
  # For smaller hands or tighter tolerance
  pinch_threshold_min: 1.9
  pinch_threshold_max: 2.9
  
  # For larger hands or looser tolerance
  pinch_threshold_min: 2.2
  pinch_threshold_max: 3.3
```

## Regular Maintenance

### Weekly

- Check webcam lens for dust
- Verify no physical obstructions
- Test all gesture types
- Monitor for any performance degradation

### Monthly

- Review logs for recurring errors
- Run full test suite: `pytest tests/`
- Benchmark performance: `python scripts/benchmark.py`
- Update configuration if needed

### Quarterly

- Update dependencies: `pip install --upgrade -r requirements.txt`
- Check for new MediaPipe versions (better performance/accuracy)
- Re-run calibration
- Review and optimize configuration

## Backup & Reset

### Backup Configuration

```bash
cp config.yaml config.yaml.backup
cp data/calibration_profile.json data/calibration_profile.json.backup
```

### Reset to Defaults

```bash
cp resources/sample_config.yaml config.yaml
rm data/calibration_profile.json
python scripts/calibrate.py
```

### Restore from Backup

```bash
cp config.yaml.backup config.yaml
cp data/calibration_profile.json.backup data/calibration_profile.json
```

## Testing Gestures

### Interactive Gesture Test

```bash
python scripts/test_gestures.py
```

Features:
- Real-time gesture feedback
- Gesture frequency counter
- False positive detector
- Performance profiling

### Unit Tests

```bash
pytest tests/ -v
```

Run specific test:
```bash
pytest tests/test_gesture_detector.py -v
```

With coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

## Multi-User Setup

### Per-User Configuration

1. Create profile for each user:
   ```bash
   cp config.yaml config_user1.yaml
   cp config.yaml config_user2.yaml
   ```

2. Edit each profile with user-specific settings

3. Run with specific profile:
   ```bash
   python main.py --config config_user1.yaml
   ```

### Shared Settings

Store common settings in one file, user-specific in separate files:
```yaml
# config_user1.yaml
cursor_control:
  speed_multiplier: 1.2
gesture_detection:
  pinch_threshold_min: 1.9
```

## Troubleshooting Performance

### Profile CPU Usage

```bash
python scripts/profile_performance.py
```

Generates report showing:
- Function call frequency
- CPU time per function
- Memory allocation

### Check System Resources

```bash
# macOS/Linux
top -p $(pgrep -f "python main.py")

# Windows
tasklist /FI "IMAGENAME eq python.exe"
```

Target metrics:
- CPU: < 60% (normal), < 80% (acceptable)
- Memory: < 300MB
- FPS: >= 25

## Documentation

- **SETUP.md**: Installation instructions
- **MAINTENANCE.md**: This file - operation guidelines
- **UPGRADE.md**: Modification and upgrade procedures
- **docs/TROUBLESHOOTING.md**: Common issues
- **docs/ARCHITECTURE.md**: System design
- **docs/GESTURE_MAPPING.md**: Gesture definitions
- **docs/PERFORMANCE_TUNING.md**: Performance optimization

## Getting Support

For issues:
1. Check TROUBLESHOOTING.md
2. Review logs in gestureglide.log
3. Run benchmark: `python scripts/benchmark.py`
4. Check GitHub issues
5. Consult documentation
