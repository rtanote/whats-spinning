# Technical Specification: whats-spinning

## System Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Audio Source    │     │  Main Process    │     │   External      │
│ (Line In)       │────▶│                  │────▶│   Services      │
└─────────────────┘     │  ┌────────────┐  │     └─────────────────┘
                        │  │ Audio      │  │            │
                        │  │ Monitor    │  │            ▼
                        │  └─────┬──────┘  │     ┌─────────────────┐
                        │        │         │     │ ACRCloud API    │
                        │        ▼         │     └─────────────────┘
                        │  ┌────────────┐  │            │
                        │  │ Recognizer │  │◀───────────┘
                        │  └─────┬──────┘  │
                        │        │         │     ┌─────────────────┐
                        │        ▼         │     │ LaMetric Time   │
                        │  ┌────────────┐  │────▶│ (Local API)     │
                        │  │ Display    │  │     └─────────────────┘
                        │  └─────┬──────┘  │
                        │        │         │     ┌─────────────────┐
                        │        ▼         │     │ Local Storage   │
                        │  ┌────────────┐  │────▶│ (JSON Log)      │
                        │  │ Logger     │  │     └─────────────────┘
                        │  └────────────┘  │
                        └──────────────────┘
```

## Tech Stack

### Language & Runtime
- Python 3.11+
- Lightweight libraries only (Zero W compatible)

### Dependencies

| Library | Purpose | Rationale |
|---------|---------|-----------|
| sounddevice | Audio input | PortAudio wrapper, cross-platform |
| numpy | Volume calculation | Required for RMS→dB conversion (minimal use) |
| requests | HTTP communication | ACRCloud, LaMetric API calls |
| zeroconf | mDNS discovery | LaMetric device auto-discovery |

### Alternatives (if too heavy on Zero W)
- sounddevice → subprocess + arecord
- numpy → Pure Python RMS calculation

## Module Structure

```
whats-spinning/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration management
│   ├── audio_monitor.py     # Audio input & volume monitoring
│   ├── recognizer.py        # ACRCloud API integration
│   ├── lametric.py          # LaMetric display
│   ├── logger.py            # Recognition log storage
│   └── state.py             # State management (cooldown, etc.)
├── tests/
│   ├── test_audio_monitor.py
│   ├── test_recognizer.py
│   └── test_lametric.py
├── docs/
│   ├── PRD.md
│   ├── TSD.md
│   └── Tasks.md
├── config.example.yaml      # Sample config file
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Module Details

### config.py

```python
# Priority: Environment variables > config.yaml > Default values
# Use pydantic-settings or dataclass for type safety
```

Configuration items:
- ACRCloud credentials
- Audio device settings
- Threshold & timing settings
- LaMetric connection info
- Logging settings

### audio_monitor.py

Responsibilities:
- List and select input devices
- Continuous volume monitoring (low-overhead chunk processing)
- Threshold detection
- Silence detection
- Recording buffer management

Main classes/functions:
```python
class AudioMonitor:
    def __init__(self, device: str, sample_rate: int = 44100)
    def list_devices() -> list[dict]  # static
    def get_current_db() -> float
    def is_above_threshold() -> bool
    def is_silence() -> bool
    def record(duration_sec: float) -> bytes  # WAV format
```

Volume calculation:
```python
# RMS to dB conversion
rms = np.sqrt(np.mean(samples ** 2))
db = 20 * np.log10(rms + 1e-10)  # Prevent division by zero
```

### recognizer.py

Responsibilities:
- ACRCloud API communication
- Request construction (signature generation)
- Response parsing

Main classes/functions:
```python
class ACRCloudRecognizer:
    def __init__(self, access_key: str, access_secret: str)
    def recognize(audio_data: bytes) -> RecognitionResult | None

@dataclass
class RecognitionResult:
    title: str
    artist: str
    album: str | None
    duration_ms: int | None
    spotify_id: str | None  # For future use
    raw_response: dict      # Store raw data
```

ACRCloud API spec:
- Endpoint: `https://identify-ap-southeast-1.acrcloud.com/v1/identify`
- Method: POST (multipart/form-data)
- Authentication: HMAC-SHA1 signature
- Audio format: WAV, MP3, etc. supported

### lametric.py

Responsibilities:
- LaMetric device discovery (mDNS)
- Send notifications via Local API

Main classes/functions:
```python
class LaMetricClient:
    def __init__(self, ip: str | None, api_key: str)
    def discover() -> str | None  # Discover IP via mDNS
    def push_notification(text: str, icon: str | None = None)
```

LaMetric Local API:
- Endpoint: `https://{ip}:4343/api/v2/device/notifications`
- Authentication: Basic auth (user: "dev", password: API Key)
- SSL: Self-signed certificate (verify=False required)

Notification JSON:
```json
{
  "priority": "info",
  "model": {
    "cycles": 1,
    "frames": [
      {
        "icon": "i9218",
        "text": "Track Name - Artist"
      }
    ]
  }
}
```

### state.py

Responsibilities:
- Cooldown state management
- Track last recognized song
- Silence duration tracking

Main classes/functions:
```python
class StateManager:
    def __init__(self, cooldown_sec: int)
    def can_recognize() -> bool
    def on_recognition(result: RecognitionResult)
    def on_silence()
    def update_silence_duration(is_silent: bool, delta_sec: float)
```

### logger.py

Responsibilities:
- Save recognition results to JSON
- File rotation (optional)

Storage format:
```json
{
  "recognized_at": "2026-01-25T15:30:00+09:00",
  "title": "Track Name",
  "artist": "Artist",
  "album": "Album Name",
  "raw_response": { ... }
}
```

### main.py

Main loop:
```python
while True:
    # 1. Check volume
    if audio_monitor.is_above_threshold():
        if state.can_recognize():
            # 2. Record
            audio_data = audio_monitor.record(config.recognition_duration)
            
            # 3. Recognize
            result = recognizer.recognize(audio_data)
            
            if result:
                # 4. Display
                lametric.push_notification(f"{result.title} - {result.artist}")
                
                # 5. Log
                logger.log(result)
                
                # 6. Start cooldown
                state.on_recognition(result)
    
    # Silence detection resets cooldown
    if audio_monitor.is_silence():
        state.update_silence_duration(True, loop_interval)
    else:
        state.update_silence_duration(False, 0)
    
    time.sleep(0.1)  # Check every 100ms
```

## Platform-Specific Considerations

### macOS Development Environment

- Specify input device via sounddevice
- Microphone access permission required in "Security & Privacy"
- Device name examples: "USB Audio Device", "Built-in Microphone"

### Raspberry Pi Zero W

- Raspberry Pi OS Lite recommended
- USB audio interface required
- Check ALSA device name: `arecord -l`
- Memory constraints: Minimize numpy usage or use pure Python alternative
- Daemonize with systemd

systemd unit file example:
```ini
[Unit]
Description=Whats Spinning
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/whats-spinning
ExecStart=/home/pi/whats-spinning/venv/bin/python src/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Error Handling

| Situation | Response |
|-----------|----------|
| ACRCloud API error | Log and wait for next trigger |
| ACRCloud recognition failure | Ignore (no LaMetric display) |
| LaMetric connection failure | Log and continue recognition |
| Audio device error | Fatal error, exit process |
| Invalid config file | Display error and exit at startup |

## Security Considerations

- Store API keys in environment variables or config file (.gitignore)
- LaMetric Local API uses self-signed certificate, SSL verification skipped
- Assumes operation within same LAN
