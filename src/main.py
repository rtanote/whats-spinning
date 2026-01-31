"""Main entry point for whats-spinning."""

from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path

from .audio_monitor import AudioMonitor
from .config import load_config
from .lametric import LaMetricClient
from .logger import RecognitionLogger
from .recognizer import ACRCloudRecognizer
from .state import StateManager


class WhatSpinning:
    """Main application class."""

    def __init__(self, config_path: str | None = None, dry_run: bool = False):
        """
        Initialize application.

        Args:
            config_path: Path to config file.
            dry_run: If True, don't send notifications to LaMetric.
        """
        self.dry_run = dry_run
        self.running = False

        # Load configuration
        print("Loading configuration...")
        try:
            self.config = load_config(config_path)
        except (FileNotFoundError, ValueError) as e:
            print(f"Configuration error: {e}")
            sys.exit(1)

        # Initialize components
        print("Initializing components...")

        # Audio monitor
        try:
            self.audio_monitor = AudioMonitor(
                device=self.config.audio.input_device,
                sample_rate=self.config.audio.sample_rate,
                volume_threshold_db=self.config.audio.volume_threshold_db,
                silence_threshold_db=self.config.audio.silence_threshold_db,
            )
            print(f"Audio monitor initialized (device: {self.config.audio.input_device or 'default'})")
        except ValueError as e:
            print(f"Audio error: {e}")
            sys.exit(1)

        # Recognizer
        self.recognizer = ACRCloudRecognizer(
            access_key=self.config.acrcloud.access_key,
            access_secret=self.config.acrcloud.access_secret,
            host=self.config.acrcloud.host,
        )
        print("ACRCloud recognizer initialized")

        # LaMetric client
        if not dry_run:
            self.lametric = LaMetricClient(
                ip=self.config.lametric.ip,
                api_key=self.config.lametric.api_key,
                icon=self.config.lametric.icon,
            )
            if self.lametric.ip:
                print(f"LaMetric client initialized (IP: {self.lametric.ip})")
            else:
                print("Warning: LaMetric not available, running in dry-run mode")
                self.dry_run = True
        else:
            self.lametric = None
            print("Running in dry-run mode (no LaMetric notifications)")

        # Logger
        self.logger = RecognitionLogger(log_file_path=self.config.logging.log_file_path)
        print(f"Logger initialized (file: {self.config.logging.log_file_path})")

        # State manager
        self.state = StateManager(
            cooldown_sec=self.config.recognition.cooldown_sec,
            silence_duration_sec=self.config.audio.silence_duration_sec,
            max_failed_attempts=self.config.recognition.max_failed_attempts,
            pause_duration_sec=self.config.recognition.pause_duration_sec,
        )
        print("State manager initialized")

    def run(self) -> None:
        """Run main loop."""
        self.running = True
        print("\n" + "=" * 50)
        print("whats-spinning is running")
        print("=" * 50)
        print(f"Volume threshold: {self.config.audio.volume_threshold_db} dB")
        print(f"Silence threshold: {self.config.audio.silence_threshold_db} dB")
        print(f"Recognition duration: {self.config.audio.recognition_duration_sec}s")
        print(f"Cooldown: {self.config.recognition.cooldown_sec}s")
        print("\nPress Ctrl+C to stop")
        print("=" * 50 + "\n")

        loop_interval = 0.1  # 100ms

        try:
            while self.running:
                # Check volume
                current_db = self.audio_monitor.get_current_db(duration=loop_interval)

                # Check if above threshold
                if current_db > self.config.audio.volume_threshold_db:
                    if self.state.can_recognize():
                        print(f"\n[TRIGGER] Volume: {current_db:.2f} dB")

                        # Record
                        audio_data = self.audio_monitor.record(
                            self.config.audio.recognition_duration_sec
                        )

                        # Recognize
                        result = self.recognizer.recognize(audio_data)

                        if result:
                            # Recognition succeeded
                            # Check if same track as last recognition
                            is_same = self.state.is_same_track(result)

                            if is_same:
                                print(f"Same track detected: {result.title} - {result.artist}")
                                print("Skipping duplicate notification and logging")
                            else:
                                # Display on LaMetric (only if different track)
                                if not self.dry_run and self.lametric:
                                    display_text = f"{result.title} - {result.artist}"
                                    self.lametric.push_notification(
                                        display_text,
                                        cycles=self.config.lametric.cycles,
                                        lifetime=self.config.lametric.lifetime
                                    )
                                else:
                                    print(f"[DRY-RUN] Would display: {result.title} - {result.artist}")

                                # Log (only if different track)
                                self.logger.log(result)

                            # Start cooldown (even for duplicate tracks)
                            self.state.on_recognition(result)
                            print(f"Cooldown started ({self.config.recognition.cooldown_sec}s)")
                        else:
                            # Recognition failed
                            print("Recognition failed - no match found")
                            self.state.on_recognition_failed()
                    else:
                        # In cooldown or paused - skip recognition
                        status = self.state.get_status()

                        # Check if paused
                        if status.get("paused", False):
                            pause_remaining = status.get("pause_remaining_sec", 0)
                            if pause_remaining > 0:
                                failures = status.get("consecutive_failures", 0)
                                print(f"\r[PAUSED] {pause_remaining/60:.1f}min remaining | Failures: {failures}    ", end="")
                                sys.stdout.flush()
                        else:
                            # In cooldown
                            remaining = status.get("cooldown_remaining_sec", 0)
                            if remaining > 0:
                                last_track = status.get("last_recognized", {})
                                track_info = f"{last_track.get('title', 'Unknown')} - {last_track.get('artist', 'Unknown')}"
                                print(f"\r[COOLDOWN] {remaining:.0f}s | Last: {track_info}    ", end="")
                                sys.stdout.flush()

                # Check for silence
                is_silent = current_db < self.config.audio.silence_threshold_db
                silence_detected = self.state.update_silence_duration(is_silent, loop_interval)

                # Delete LaMetric notification when silence is detected
                if silence_detected and not self.dry_run and self.lametric:
                    self.lametric.delete_notification()

                time.sleep(loop_interval)

        except KeyboardInterrupt:
            print("\n\nShutting down gracefully...")
            self.running = False

    def stop(self) -> None:
        """Stop the application."""
        self.running = False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="whats-spinning: Automatic music recognition for analog playback"
    )
    parser.add_argument(
        "--config",
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Recognize but don't send to LaMetric",
    )

    args = parser.parse_args()

    # Create application
    app = WhatSpinning(config_path=args.config, dry_run=args.dry_run)

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print("\nReceived signal, stopping...")
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run
    app.run()


if __name__ == "__main__":
    main()
