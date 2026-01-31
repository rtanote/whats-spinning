# Tasks: whats-spinning

## Phase 1: Foundation (macOS Development Environment)

### Task 1.1: Project Initialization
- [ ] Create directory structure
- [ ] Create requirements.txt (sounddevice, numpy, requests, zeroconf)
- [ ] Create requirements-dev.txt (pytest, black, ruff)
- [ ] Create config.example.yaml
- [ ] Create .gitignore
- [ ] Create README.md

### Task 1.2: Configuration Management Module
- [ ] Implement config.py
  - Load from environment variables
  - Load from YAML file
  - Set default values
  - Type validation
- [ ] Define all configuration items (as listed in PRD)

### Task 1.3: Audio Input & Monitoring Module
- [ ] Implement audio_monitor.py
  - list_devices(): List available devices
  - Device selection & initialization
  - get_current_db(): Get current volume level
  - is_above_threshold(): Threshold check
  - is_silence(): Silence detection
  - record(): Record for specified duration (WAV format)
- [ ] Verify on macOS
- [ ] Add CLI command for device listing

**Test commands:**
```bash
python -m src.audio_monitor --list-devices
python -m src.audio_monitor --monitor  # Real-time dB display
```

## Phase 2: API Integration

### Task 2.1: ACRCloud Recognition Module
- [ ] Implement recognizer.py
  - HMAC-SHA1 signature generation
  - Build multipart/form-data request
  - Parse response
  - RecognitionResult dataclass
- [ ] Unit tests (with mocks)
- [ ] Test with actual API calls

**Test CLI:**
```bash
python -m src.recognizer --file test.wav
```

### Task 2.2: LaMetric Integration Module
- [ ] Implement lametric.py
  - discover(): Device discovery via mDNS
  - push_notification(): Send notification
  - Handle self-signed SSL certificate
- [ ] Unit tests
- [ ] Verify display on actual device

**Test CLI:**
```bash
python -m src.lametric --discover
python -m src.lametric --push "Test message"
```

### Task 2.3: Logging Module
- [ ] Implement logger.py
  - Append to JSON Lines format
  - ISO8601 timestamp
  - Store raw response
- [ ] Log file read/display feature (for debugging)

## Phase 3: Integration & Main Loop

### Task 3.1: State Management Module
- [ ] Implement state.py
  - Cooldown management
  - Silence duration tracking
  - Track end detection (reset after sustained silence)
- [ ] Unit tests

### Task 3.2: Main Loop Implementation
- [ ] Implement main.py
  - Load configuration
  - Initialize all modules
  - Main loop (volume monitor → record → recognize → display → log)
  - Graceful shutdown (Ctrl+C handling)
- [ ] Integration test (macOS)

**Run commands:**
```bash
python -m src.main
python -m src.main --config config.yaml
python -m src.main --dry-run  # Recognize but don't send to LaMetric
```

### Task 3.3: E2E Testing on macOS
- [ ] Test with line input from mixer
- [ ] Tune volume threshold
- [ ] Verify cooldown behavior
- [ ] Verify silence detection → reset
- [ ] Test recognition accuracy (noise tolerance, etc.)

## Phase 4: Raspberry Pi Zero W Port

### Task 4.1: Pi Setup Documentation
- [ ] Raspberry Pi OS Lite installation guide
- [ ] Initial setup (Wi-Fi, SSH enable)
- [ ] Required package installation guide
  - python3-pip
  - libportaudio2
  - alsa-utils
- [ ] USB audio interface verification guide

### Task 4.2: Pi Optimization (as needed)
- [ ] Reduce numpy dependency (pure Python RMS calculation)
- [ ] Alternative implementation: sounddevice → subprocess + arecord
- [ ] Monitor and optimize memory usage

### Task 4.3: systemd Service Setup
- [ ] Create whats-spinning.service
- [ ] Configure auto-start
- [ ] Configure logging (journald)
- [ ] Verify auto-recovery on restart

### Task 4.4: Pi Testing
- [ ] Verify input from USB audio interface
- [ ] Long-running stability test
- [ ] Check for memory leaks
- [ ] Monitor API usage

## Phase 5: Polish & Documentation

### Task 5.1: Error Handling Improvements
- [ ] Behavior on network disconnection
- [ ] Behavior on API rate limiting
- [ ] Behavior on device disconnection

### Task 5.2: Documentation
- [ ] Complete README.md
  - Setup instructions
  - Configuration reference
  - Troubleshooting
- [ ] Expand config samples

### Task 5.3: Future Extension Prep (Optional)
- [ ] Design interface for cloud logging
- [ ] Research Spotify playlist integration

---

## Priority & Dependencies

```
Phase 1 ──▶ Phase 2 ──▶ Phase 3 ──▶ Phase 4
   │           │           │           │
   └─ 1.1      └─ 2.1      └─ 3.2      └─ 4.3
      1.2         2.2         3.3         4.4
      1.3         2.3
                            ▲
                            │
                         Phase 5
```

## Time Estimates

| Phase | Estimated Time |
|-------|----------------|
| Phase 1 | 2-3 hours |
| Phase 2 | 3-4 hours |
| Phase 3 | 2-3 hours |
| Phase 4 | 2-3 hours |
| Phase 5 | 1-2 hours |
| **Total** | **10-15 hours** |

## First Tasks to Start

1. **Task 1.1**: Project initialization
2. **Task 1.3**: Audio input module (quick to verify)
3. **Task 2.1**: ACRCloud integration (validate core functionality)

Once these three are working, minimal end-to-end verification is possible.
