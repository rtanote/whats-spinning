# PRD: whats-spinning

## Overview

A system that automatically recognizes music playing from analog playback devices (turntables, CD players, etc.) and displays the track name and artist on a LaMetric Time device.

## Background & Problem

- When playing records or CDs, you often don't know the track name
- Manually launching Shazam every time is tedious
- Analog playback devices don't have metadata display capabilities

## Goals

- Automatically recognize music when it starts playing and display track info on LaMetric
- Don't call the recognition API during silence (conserve free tier quota)
- Eventually run 24/7 on a Raspberry Pi Zero W

## User Stories

1. User plays a record/CD
2. System detects audio input volume exceeding threshold
3. System calls ACRCloud API to recognize the track
4. LaMetric Time displays "Track Name - Artist"
5. Recognition result is saved to log/storage
6. Cooldown period prevents duplicate recognition of the same track
7. When the track ends (silence detected), cooldown resets

## Functional Requirements

### Audio Input
- Capture audio from line input
- macOS: Core Audio device selection
- Raspberry Pi: USB audio interface

### Volume Trigger
- Threshold setting in dB (default: around -40dB, adjustable)
- Start recording when threshold is exceeded
- Silence detection for track end detection

### Music Recognition
- Use ACRCloud API
- Recording duration for recognition: ~10 seconds
- On recognition failure: ignore (no LaMetric display)

### LaMetric Display
- Push via Local API (same LAN)
- Device discovery via mDNS
- Display format: "Track Name - Artist"
- Scroll speed depends on device settings

### Cooldown
- Prevent consecutive recognition of the same track after successful recognition
- Default: 2 minutes
- Reset on silence detection

### Logging/Storage
- Save recognition results in JSON format
- Storage: Local file (cloud integration considered for future)
- Saved info: track name, artist, album, recognition timestamp, raw ACRCloud response

## Non-Functional Requirements

### Platforms
- Development/Testing: macOS
- Production: Raspberry Pi Zero W (Raspberry Pi OS Lite)

### Performance
- Volume monitoring: continuous (low overhead)
- Recognition processing: only on trigger
- Lightweight implementation that runs on Zero W

### API Usage
- ACRCloud free tier: 1000 requests/month
- Conserved via volume trigger + cooldown

## Configuration (Environment Variables or Config File)

| Item | Description | Default |
|------|-------------|---------|
| ACRCLOUD_ACCESS_KEY | ACRCloud API key | - |
| ACRCLOUD_ACCESS_SECRET | ACRCloud API secret | - |
| AUDIO_INPUT_DEVICE | Input device name | System default |
| VOLUME_THRESHOLD_DB | Volume threshold (dB) | -40 |
| SILENCE_THRESHOLD_DB | Silence detection threshold (dB) | -50 |
| SILENCE_DURATION_SEC | Silence duration for track end detection | 5 |
| RECOGNITION_DURATION_SEC | Recording duration for recognition | 10 |
| COOLDOWN_SEC | Cooldown duration | 120 |
| LAMETRIC_IP | LaMetric IP address (mDNS if not specified) | - |
| LAMETRIC_API_KEY | LaMetric Local API key | - |
| LOG_FILE_PATH | Recognition log file path | ./recognition_log.json |

## Future Enhancements

- Log recognition results to Google Sheets
- Auto-add to Spotify playlist
- Simultaneous display on multiple LaMetric devices
- Web dashboard for recognition history
