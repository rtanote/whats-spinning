"""State management module for cooldown and silence tracking."""

from __future__ import annotations

import time

from .recognizer import RecognitionResult


class StateManager:
    """Manage recognition state (cooldown, silence tracking)."""

    def __init__(
        self,
        cooldown_sec: int = 120,
        silence_duration_sec: float = 5.0,
        max_failed_attempts: int = 3,
        pause_duration_sec: int = 900,  # 15 minutes
    ):
        """
        Initialize state manager.

        Args:
            cooldown_sec: Cooldown duration in seconds.
            silence_duration_sec: Silence duration to reset cooldown.
            max_failed_attempts: Maximum consecutive failed recognitions before pausing.
            pause_duration_sec: Duration to pause recognition after max failures.
        """
        self.cooldown_sec = cooldown_sec
        self.silence_duration_sec = silence_duration_sec
        self.max_failed_attempts = max_failed_attempts
        self.pause_duration_sec = pause_duration_sec

        # State
        self.last_recognition_time: float | None = None
        self.last_result: RecognitionResult | None = None
        self.silence_start_time: float | None = None
        self.cumulative_silence_duration: float = 0.0

        # Failed recognition tracking
        self.consecutive_failures: int = 0
        self.paused_until: float | None = None

        # Notification deletion tracking
        self.notification_deleted: bool = False

    def can_recognize(self) -> bool:
        """
        Check if recognition is allowed (not in cooldown or paused).

        Returns:
            True if recognition is allowed.
        """
        # Check if paused due to consecutive failures
        if self.paused_until is not None:
            if time.time() < self.paused_until:
                return False
            else:
                # Pause expired, reset
                self.paused_until = None
                self.consecutive_failures = 0

        if self.last_recognition_time is None:
            return True

        elapsed = time.time() - self.last_recognition_time
        return elapsed >= self.cooldown_sec

    def is_same_track(self, result: RecognitionResult) -> bool:
        """
        Check if the result is the same as the last recognized track.

        Args:
            result: Recognition result to check.

        Returns:
            True if same track.
        """
        if not self.last_result:
            return False

        return (
            result.title == self.last_result.title
            and result.artist == self.last_result.artist
        )

    def should_repush_notification(self) -> bool:
        """
        Check if notification should be re-pushed (after deletion due to silence).

        Returns:
            True if notification was deleted and should be re-pushed.
        """
        return self.notification_deleted

    def reset_notification_deleted(self) -> None:
        """Reset the notification deleted flag."""
        self.notification_deleted = False

    def on_recognition(self, result: RecognitionResult) -> None:
        """
        Called when recognition succeeds.

        Args:
            result: Recognition result.
        """
        self.last_recognition_time = time.time()
        self.last_result = result
        # Reset silence tracking
        self._reset_silence()
        # Reset failure counter on successful recognition
        self.consecutive_failures = 0

    def on_recognition_failed(self) -> None:
        """Called when recognition fails (no match found)."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.max_failed_attempts:
            self.paused_until = time.time() + self.pause_duration_sec
            print(
                f"Too many failed recognitions ({self.consecutive_failures}). "
                f"Pausing recognition for {self.pause_duration_sec // 60} minutes"
            )

    def on_silence(self) -> None:
        """Called when sustained silence is detected (resets cooldown)."""
        print("Sustained silence detected, resetting cooldown")
        self.last_recognition_time = None
        self.last_result = None
        self.notification_deleted = True
        self._reset_silence()

    def update_silence_duration(self, is_silent: bool, delta_sec: float) -> bool:
        """
        Update silence duration tracking.

        Args:
            is_silent: True if currently silent.
            delta_sec: Time elapsed since last update.

        Returns:
            True if sustained silence was just detected.
        """
        if is_silent:
            if self.silence_start_time is None:
                self.silence_start_time = time.time()
            self.cumulative_silence_duration += delta_sec

            # Check if sustained silence threshold reached
            if self.cumulative_silence_duration >= self.silence_duration_sec:
                self.on_silence()
                return True
        else:
            # Reset silence tracking if sound detected
            self._reset_silence()

        return False

    def _reset_silence(self) -> None:
        """Reset silence tracking state."""
        self.silence_start_time = None
        self.cumulative_silence_duration = 0.0

    def get_status(self) -> dict[str, any]:
        """
        Get current state status.

        Returns:
            Status dictionary.
        """
        status = {
            "can_recognize": self.can_recognize(),
            "in_cooldown": not self.can_recognize(),
        }

        if self.last_recognition_time:
            elapsed = time.time() - self.last_recognition_time
            remaining = max(0, self.cooldown_sec - elapsed)
            status["cooldown_elapsed_sec"] = elapsed
            status["cooldown_remaining_sec"] = remaining

        if self.last_result:
            status["last_recognized"] = {
                "title": self.last_result.title,
                "artist": self.last_result.artist,
            }

        status["silence_duration_sec"] = self.cumulative_silence_duration

        # Pause status
        status["consecutive_failures"] = self.consecutive_failures
        if self.paused_until is not None:
            pause_remaining = max(0, self.paused_until - time.time())
            status["paused"] = True
            status["pause_remaining_sec"] = pause_remaining
        else:
            status["paused"] = False

        return status
