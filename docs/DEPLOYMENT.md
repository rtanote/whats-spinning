# Raspberry Pi Deployment Guide

This guide explains how to deploy whats-spinning on a Raspberry Pi Zero W.

## Prerequisites

- Raspberry Pi Zero W (or any Raspberry Pi with WiFi)
- Raspberry Pi OS Lite (Debian-based)
- USB audio interface (e.g., MG-XU) connected to the Pi
- LaMetric Time on the same network
- ACRCloud account credentials

## 1. Raspberry Pi OS Setup

### Install Raspberry Pi OS

1. Download Raspberry Pi OS Lite from https://www.raspberrypi.com/software/
2. Flash to SD card using Raspberry Pi Imager
3. Enable SSH before first boot:
   ```bash
   # On macOS/Linux, mount the boot partition and create ssh file
   touch /Volumes/boot/ssh
   ```

### Initial Configuration

1. Boot the Pi and SSH into it:
   ```bash
   ssh pi@raspberrypi.local
   # Default password: raspberry
   ```

2. Update the system:
   ```bash
   sudo apt update
   sudo apt upgrade -y
   ```

3. Run raspi-config for basic setup:
   ```bash
   sudo raspi-config
   ```
   - Set hostname (e.g., "whats-spinning")
   - Configure WiFi
   - Change default password
   - Set timezone
   - Expand filesystem

## 2. Install Dependencies

### System Dependencies

```bash
# Python 3 and pip
sudo apt install -y python3 python3-pip python3-venv

# Audio libraries
sudo apt install -y portaudio19-dev python3-pyaudio

# Git (if cloning from GitHub)
sudo apt install -y git
```

### Audio Device Configuration

1. Connect your USB audio interface

2. List audio devices:
   ```bash
   arecord -l
   ```

3. Test audio recording:
   ```bash
   arecord -D plughw:CARD=CODEC,DEV=0 -d 5 test.wav
   aplay test.wav
   ```

## 3. Install whats-spinning

### Option 1: Clone from GitHub

```bash
cd ~
git clone https://github.com/rtanote/whats-spinning.git
cd whats-spinning
```

### Option 2: Transfer from Development Machine

From your Mac:
```bash
# Create a tarball excluding config.yaml and other sensitive files
tar czf whats-spinning.tar.gz \
  --exclude='config.yaml' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='venv' \
  --exclude='recognition_log.json' \
  whats-spinning/

# Transfer to Pi
scp whats-spinning.tar.gz pi@raspberrypi.local:~

# On the Pi
ssh pi@raspberrypi.local
tar xzf whats-spinning.tar.gz
cd whats-spinning
```

### Install Python Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Configuration

### Create Configuration File

```bash
# Copy example config
cp config.example.yaml config.yaml

# Edit with your credentials
nano config.yaml
```

Update the following fields:
- `acrcloud.access_key`: Your ACRCloud access key
- `acrcloud.access_secret`: Your ACRCloud access secret
- `audio.input_device`: Your audio device name (or null for default)
- `lametric.ip`: Your LaMetric IP address (or null for auto-discovery)
- `lametric.api_key`: Your LaMetric API key
- `lametric.icon`: Icon ID (e.g., "i2020")

### Test Configuration

```bash
# Activate virtual environment
source venv/bin/activate

# Run in dry-run mode to test
python -m whats_spinning --dry-run
```

## 5. Systemd Service Setup

### Create Service File

```bash
sudo nano /etc/systemd/system/whats-spinning.service
```

Add the following content (adjust paths as needed):

```ini
[Unit]
Description=whats-spinning - Automatic music recognition for analog playback
After=network.target sound.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/whats-spinning
Environment="PATH=/home/pi/whats-spinning/venv/bin"
ExecStart=/home/pi/whats-spinning/venv/bin/python -m whats_spinning
Restart=on-failure
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable whats-spinning

# Start service now
sudo systemctl start whats-spinning

# Check status
sudo systemctl status whats-spinning
```

### View Logs

```bash
# Follow logs in real-time
sudo journalctl -u whats-spinning -f

# View recent logs
sudo journalctl -u whats-spinning -n 50
```

## 6. Service Management

### Common Commands

```bash
# Start service
sudo systemctl start whats-spinning

# Stop service
sudo systemctl stop whats-spinning

# Restart service
sudo systemctl restart whats-spinning

# Check status
sudo systemctl status whats-spinning

# View logs
sudo journalctl -u whats-spinning -f
```

### Update Configuration

After changing config.yaml:
```bash
sudo systemctl restart whats-spinning
```

### Update Code

```bash
cd ~/whats-spinning

# If using git
git pull

# If transferring files
# (transfer updated files from your Mac first)

# Restart service
sudo systemctl restart whats-spinning
```

## 7. Troubleshooting

### Audio Device Not Found

```bash
# List all audio devices
arecord -l

# Test recording
arecord -D plughw:CARD=CODEC,DEV=0 -d 5 test.wav
aplay test.wav
```

Update `audio.input_device` in config.yaml with the correct device name.

### LaMetric Not Found

```bash
# Check network connectivity
ping 192.168.3.7  # Your LaMetric IP

# Test mDNS discovery
avahi-browse -a
```

Try setting `lametric.ip` explicitly in config.yaml instead of using auto-discovery.

### Service Won't Start

```bash
# Check service status
sudo systemctl status whats-spinning

# View detailed logs
sudo journalctl -u whats-spinning -n 100

# Test manually
cd ~/whats-spinning
source venv/bin/activate
python -m whats_spinning --dry-run
```

### High CPU Usage

Raspberry Pi Zero W is less powerful than your Mac. If you experience high CPU usage:

1. Increase `recognition.cooldown_sec` to reduce API calls
2. Consider using a more powerful Pi (Pi 3/4) for better performance

## 8. Performance Optimization

### For Raspberry Pi Zero W

The Pi Zero W is single-core and less powerful. Consider these optimizations:

1. Increase loop interval in code if needed
2. Reduce audio sample rate if recognition accuracy allows
3. Use longer cooldown periods

### For Better Performance

Consider upgrading to:
- Raspberry Pi 3 Model B+ (quad-core)
- Raspberry Pi 4 Model B (quad-core, more RAM)

## 9. Security Considerations

1. Change default Pi password
2. Keep config.yaml permissions restrictive:
   ```bash
   chmod 600 config.yaml
   ```
3. Disable SSH password authentication (use SSH keys)
4. Keep system updated:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

## 10. Backup

### Backup Configuration

```bash
# Backup config.yaml to a secure location
scp pi@raspberrypi.local:~/whats-spinning/config.yaml ~/backup/
```

### Backup Recognition Log

```bash
# Copy recognition log
scp pi@raspberrypi.local:~/whats-spinning/recognition_log.json ~/backup/
```
