"""Audio input and monitoring module."""

from __future__ import annotations

import io
import sys
import wave
from typing import Any

import numpy as np
import sounddevice as sd


class AudioMonitor:
    """Monitor audio input and detect volume levels."""

    def __init__(
        self,
        device: str | None = None,
        sample_rate: int = 44100,
        volume_threshold_db: float = -40.0,
        silence_threshold_db: float = -50.0,
    ):
        """
        Initialize audio monitor.

        Args:
            device: Audio input device name. None for system default.
            sample_rate: Sample rate in Hz.
            volume_threshold_db: Volume threshold for trigger in dB.
            silence_threshold_db: Silence threshold in dB.
        """
        self.device = device
        self.sample_rate = sample_rate
        self.volume_threshold_db = volume_threshold_db
        self.silence_threshold_db = silence_threshold_db
        self.channels = 1  # Mono

        # Verify device exists
        if device is not None:
            devices = self.list_devices()
            if not any(d["name"] == device for d in devices if d["max_input_channels"] > 0):
                available = [d["name"] for d in devices if d["max_input_channels"] > 0]
                raise ValueError(
                    f"Audio device '{device}' not found. Available input devices: {available}"
                )

    @staticmethod
    def list_devices() -> list[dict[str, Any]]:
        """
        List available audio input devices.

        Returns:
            List of device info dictionaries.
        """
        devices = sd.query_devices()
        result = []
        for i, dev in enumerate(devices):
            result.append(
                {
                    "index": i,
                    "name": dev["name"],
                    "max_input_channels": dev["max_input_channels"],
                    "max_output_channels": dev["max_output_channels"],
                    "default_sample_rate": dev["default_samplerate"],
                }
            )
        return result

    def _calculate_db(self, audio_data: np.ndarray) -> float:
        """
        Calculate RMS volume in dB.

        Args:
            audio_data: Audio samples as numpy array.

        Returns:
            Volume level in dB.
        """
        # Calculate RMS
        rms = np.sqrt(np.mean(audio_data**2))
        # Convert to dB (add small epsilon to avoid log(0))
        db = 20 * np.log10(rms + 1e-10)
        return float(db)

    def get_current_db(self, duration: float = 0.1) -> float:
        """
        Get current volume level.

        Args:
            duration: Duration to sample in seconds.

        Returns:
            Current volume level in dB.
        """
        recording = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            device=self.device,
            dtype="float32",
        )
        sd.wait()
        return self._calculate_db(recording.flatten())

    def is_above_threshold(self, duration: float = 0.1) -> bool:
        """
        Check if current volume exceeds threshold.

        Args:
            duration: Duration to sample in seconds.

        Returns:
            True if above threshold.
        """
        db = self.get_current_db(duration)
        return db > self.volume_threshold_db

    def is_silence(self, duration: float = 0.1) -> bool:
        """
        Check if current volume is below silence threshold.

        Args:
            duration: Duration to sample in seconds.

        Returns:
            True if silent.
        """
        db = self.get_current_db(duration)
        return db < self.silence_threshold_db

    def record(self, duration_sec: float) -> bytes:
        """
        Record audio for specified duration.

        Args:
            duration_sec: Recording duration in seconds.

        Returns:
            Audio data in WAV format (bytes).
        """
        print(f"Recording for {duration_sec} seconds...")
        recording = sd.rec(
            int(duration_sec * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            device=self.device,
            dtype="int16",  # 16-bit PCM for WAV
        )
        sd.wait()
        print("Recording complete.")

        # Convert to WAV format
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(recording.tobytes())

        return buffer.getvalue()


def main():
    """CLI for audio monitor testing."""
    import argparse
    import time

    parser = argparse.ArgumentParser(description="Audio Monitor CLI")
    parser.add_argument("--list-devices", action="store_true", help="List audio devices")
    parser.add_argument(
        "--monitor", action="store_true", help="Monitor volume in real-time"
    )
    parser.add_argument("--device", help="Audio input device name")
    parser.add_argument(
        "--threshold", type=float, default=-40.0, help="Volume threshold in dB"
    )

    args = parser.parse_args()

    if args.list_devices:
        print("Available audio input devices:")
        devices = AudioMonitor.list_devices()
        for dev in devices:
            if dev["max_input_channels"] > 0:
                print(
                    f"  [{dev['index']}] {dev['name']} "
                    f"(max input: {dev['max_input_channels']}, "
                    f"sample rate: {dev['default_sample_rate']})"
                )
        return

    if args.monitor:
        monitor = AudioMonitor(
            device=args.device, volume_threshold_db=args.threshold
        )
        print(f"Monitoring audio levels (threshold: {args.threshold} dB)")
        print("Press Ctrl+C to stop")
        try:
            while True:
                db = monitor.get_current_db(0.1)
                above = "TRIGGER" if db > args.threshold else ""
                print(f"\rCurrent level: {db:6.2f} dB {above}    ", end="")
                sys.stdout.flush()
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nStopped.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
