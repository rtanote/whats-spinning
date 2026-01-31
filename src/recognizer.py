"""ACRCloud music recognition module."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class RecognitionResult:
    """Music recognition result."""

    title: str
    artist: str
    album: str | None = None
    duration_ms: int | None = None
    spotify_id: str | None = None
    raw_response: dict[str, Any] | None = None


class ACRCloudRecognizer:
    """ACRCloud music recognizer."""

    def __init__(self, access_key: str, access_secret: str, host: str = "identify-ap-southeast-1.acrcloud.com", debug_dir: str | None = None):
        """
        Initialize recognizer.

        Args:
            access_key: ACRCloud access key.
            access_secret: ACRCloud access secret.
            host: ACRCloud API host.
            debug_dir: Directory to save failed recognition audio files (None to disable).
        """
        self.access_key = access_key
        self.access_secret = access_secret
        self.host = host
        self.endpoint = f"https://{host}/v1/identify"
        self.debug_dir = debug_dir

    def _generate_signature(
        self, method: str, uri: str, timestamp: int, string_to_sign: str
    ) -> str:
        """
        Generate HMAC-SHA1 signature.

        Args:
            method: HTTP method.
            uri: Request URI.
            timestamp: Unix timestamp.
            string_to_sign: String to sign.

        Returns:
            Base64-encoded signature.
        """
        signature_string = f"{method}\n{uri}\n{self.access_key}\naudio\n1\n{timestamp}"
        signature = hmac.new(
            self.access_secret.encode("utf-8"),
            signature_string.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        return base64.b64encode(signature).decode("utf-8")

    def recognize(self, audio_data: bytes) -> RecognitionResult | None:
        """
        Recognize music from audio data.

        Args:
            audio_data: Audio data in WAV format.

        Returns:
            RecognitionResult if successful, None otherwise.
        """
        timestamp = int(time.time())
        string_to_sign = f"{self.access_key}\naudio\n1\n{timestamp}"

        signature = self._generate_signature("POST", "/v1/identify", timestamp, string_to_sign)

        files = {"sample": ("audio.wav", audio_data, "audio/wav")}
        data = {
            "access_key": self.access_key,
            "sample_bytes": len(audio_data),
            "timestamp": timestamp,
            "signature": signature,
            "data_type": "audio",
            "signature_version": "1",
            "audio_format": "recorded",  # Disable humming detection
        }

        try:
            print("Sending recognition request to ACRCloud...")
            response = requests.post(self.endpoint, files=files, data=data, timeout=30)
            response.raise_for_status()
            result = response.json()

            # Parse response
            if result.get("status", {}).get("code") != 0:
                msg = result.get("status", {}).get("msg", "Unknown error")
                print(f"Recognition failed: {msg}")
                self._save_debug_audio(audio_data, "api_error")
                return None

            metadata = result.get("metadata")
            if not metadata or not metadata.get("music"):
                print("No music recognized")
                # Print debug info about the response
                if metadata:
                    print(f"Debug: Metadata present but no music. Keys: {list(metadata.keys())}")
                    # Check if there are low-confidence matches
                    if "custom_files" in metadata:
                        print(f"Debug: Custom files found: {len(metadata['custom_files'])}")
                else:
                    print("Debug: No metadata in response")
                self._save_debug_audio(audio_data, "no_match")
                return None

            music = metadata["music"][0]
            title = music.get("title", "Unknown")
            artists = music.get("artists", [])
            artist = artists[0]["name"] if artists else "Unknown"
            album = music.get("album", {}).get("name")
            duration_ms = music.get("duration_ms")

            # Extract Spotify ID if available
            spotify_id = None
            external_metadata = music.get("external_metadata", {})
            if "spotify" in external_metadata:
                spotify_data = external_metadata["spotify"]
                if spotify_data and "track" in spotify_data:
                    spotify_id = spotify_data["track"].get("id")

            print(f"Recognized: {title} - {artist}")

            return RecognitionResult(
                title=title,
                artist=artist,
                album=album,
                duration_ms=duration_ms,
                spotify_id=spotify_id,
                raw_response=result,
            )

        except requests.RequestException as e:
            print(f"ACRCloud API error: {e}")
            self._save_debug_audio(audio_data, "network_error")
            return None
        except (KeyError, IndexError, ValueError) as e:
            print(f"Failed to parse ACRCloud response: {e}")
            self._save_debug_audio(audio_data, "parse_error")
            return None

    def _save_debug_audio(self, audio_data: bytes, reason: str) -> None:
        """
        Save audio data for debugging purposes.

        Args:
            audio_data: Audio data to save.
            reason: Reason for failure (used in filename).
        """
        if not self.debug_dir:
            return

        try:
            from pathlib import Path
            debug_path = Path(self.debug_dir)
            debug_path.mkdir(parents=True, exist_ok=True)

            # Clean up old debug files (keep only last 10)
            self._cleanup_old_debug_files(debug_path, max_files=10)

            timestamp = int(time.time())
            filename = f"failed_{reason}_{timestamp}.wav"
            filepath = debug_path / filename

            with open(filepath, "wb") as f:
                f.write(audio_data)

            print(f"Debug: Saved audio to {filepath}")
        except Exception as e:
            print(f"Warning: Failed to save debug audio: {e}")

    def _cleanup_old_debug_files(self, debug_path, max_files: int = 10) -> None:
        """
        Remove old debug audio files, keeping only the most recent ones.

        Args:
            debug_path: Path to debug directory.
            max_files: Maximum number of files to keep.
        """
        try:
            # Get all WAV files in debug directory
            wav_files = sorted(debug_path.glob("failed_*.wav"), key=lambda p: p.stat().st_mtime)

            # Remove oldest files if exceeding max_files
            files_to_remove = len(wav_files) - max_files
            if files_to_remove > 0:
                for old_file in wav_files[:files_to_remove]:
                    old_file.unlink()
                    print(f"Debug: Removed old file {old_file.name}")
        except Exception as e:
            print(f"Warning: Failed to cleanup old debug files: {e}")


def main():
    """CLI for recognizer testing."""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="ACRCloud Recognizer CLI")
    parser.add_argument("--file", required=True, help="Audio file to recognize")
    parser.add_argument("--access-key", help="ACRCloud access key")
    parser.add_argument("--access-secret", help="ACRCloud access secret")

    args = parser.parse_args()

    # Get credentials
    access_key = args.access_key or os.getenv("ACRCLOUD_ACCESS_KEY")
    access_secret = args.access_secret or os.getenv("ACRCLOUD_ACCESS_SECRET")

    if not access_key or not access_secret:
        print("Error: ACRCloud credentials required")
        print("Set via --access-key and --access-secret or environment variables")
        return

    # Read audio file
    try:
        with open(args.file, "rb") as f:
            audio_data = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {args.file}")
        return

    # Recognize
    recognizer = ACRCloudRecognizer(access_key, access_secret)
    result = recognizer.recognize(audio_data)

    if result:
        print("\n=== Recognition Result ===")
        print(f"Title: {result.title}")
        print(f"Artist: {result.artist}")
        if result.album:
            print(f"Album: {result.album}")
        if result.duration_ms:
            print(f"Duration: {result.duration_ms / 1000:.1f}s")
        if result.spotify_id:
            print(f"Spotify ID: {result.spotify_id}")
    else:
        print("Recognition failed")


if __name__ == "__main__":
    main()
