"""Recognition logging module."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .recognizer import RecognitionResult


class RecognitionLogger:
    """Logger for music recognition results."""

    def __init__(self, log_file_path: str = "./recognition_log.json"):
        """
        Initialize logger.

        Args:
            log_file_path: Path to log file.
        """
        self.log_file_path = Path(log_file_path)
        # Ensure parent directory exists
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, result: RecognitionResult) -> None:
        """
        Log recognition result.

        Args:
            result: Recognition result to log.
        """
        entry: dict[str, Any] = {
            "recognized_at": datetime.now(timezone.utc).isoformat(),
            "title": result.title,
            "artist": result.artist,
        }

        # Add optional fields
        if result.album:
            entry["album"] = result.album
        if result.duration_ms is not None:
            entry["duration_ms"] = result.duration_ms
        if result.spotify_id:
            entry["spotify_id"] = result.spotify_id
        if result.raw_response:
            entry["raw_response"] = result.raw_response

        # Append to file (JSON Lines format)
        with open(self.log_file_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        print(f"Logged to {self.log_file_path}")

    def read_logs(self, limit: int | None = None) -> list[dict[str, Any]]:
        """
        Read log entries.

        Args:
            limit: Maximum number of entries to return (most recent first).
                  None for all entries.

        Returns:
            List of log entries.
        """
        if not self.log_file_path.exists():
            return []

        entries = []
        with open(self.log_file_path) as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        # Skip invalid lines
                        continue

        # Return most recent first
        entries.reverse()

        if limit is not None:
            entries = entries[:limit]

        return entries


def main():
    """CLI for logger testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Recognition Logger CLI")
    parser.add_argument("--read", action="store_true", help="Read log entries")
    parser.add_argument("--limit", type=int, help="Limit number of entries")
    parser.add_argument("--file", default="./recognition_log.json", help="Log file path")

    args = parser.parse_args()

    logger = RecognitionLogger(args.file)

    if args.read:
        entries = logger.read_logs(limit=args.limit)
        if not entries:
            print("No log entries found")
            return

        print(f"Found {len(entries)} entries:\n")
        for i, entry in enumerate(entries, 1):
            print(f"{i}. {entry.get('recognized_at', 'Unknown time')}")
            print(f"   {entry.get('title', 'Unknown')} - {entry.get('artist', 'Unknown')}")
            if entry.get("album"):
                print(f"   Album: {entry['album']}")
            print()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
