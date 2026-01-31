# whats-spinning

A system that automatically recognizes music playing from analog playback devices (turntables, CD players, etc.) and displays the track name and artist on a LaMetric Time device.

## Features

- Automatic music recognition using ACRCloud
- Real-time track display on LaMetric Time
- Volume-based trigger to conserve API quota
- Cooldown mechanism to prevent duplicate recognition
- JSON logging of all recognized tracks
- Optimized for Raspberry Pi Zero W

## Setup

### Requirements

- Python 3.11+
- Audio input device (USB audio interface for Raspberry Pi)
- ACRCloud account (free tier: 1000 requests/month)
- LaMetric Time device on the same LAN

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/whats-spinning.git
cd whats-spinning
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy and configure the config file:
```bash
cp config.example.yaml config.yaml
```

5. Edit `config.yaml` with your ACRCloud and LaMetric credentials.

### Configuration

You can configure the system using either:
1. YAML config file (`config.yaml`)
2. Environment variables (take priority over config file)

Environment variable names:
- `ACRCLOUD_ACCESS_KEY`
- `ACRCLOUD_ACCESS_SECRET`
- `AUDIO_INPUT_DEVICE`
- `VOLUME_THRESHOLD_DB`
- `LAMETRIC_IP`
- `LAMETRIC_API_KEY`
- etc.

See [config.example.yaml](config.example.yaml) for all available options.

## Usage

### List available audio devices
```bash
python -m src.audio_monitor --list-devices
```

### Monitor audio levels
```bash
python -m src.audio_monitor --monitor
```

### Test ACRCloud recognition
```bash
python -m src.recognizer --file test.wav
```

### Test LaMetric display
```bash
python -m src.lametric --discover
python -m src.lametric --push "Test message"
```

### Run the main program
```bash
python -m src.main
```

Or with a specific config file:
```bash
python -m src.main --config config.yaml
```

Dry-run mode (recognize but don't send to LaMetric):
```bash
python -m src.main --dry-run
```

## Raspberry Pi Deployment

See [docs/Tasks.md](docs/Tasks.md) Phase 4 for Raspberry Pi setup instructions.

## Development

Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

Run tests:
```bash
pytest
```

Format code:
```bash
black src tests
ruff check src tests
```

## License

MIT
