"""Play the win/lose sound effects bundled with the original program.

The original ships ``sounds\\win<0-9>.wav`` and ``sounds\\lose<0-9>.wav``.
We play them via MCI (no third-party deps).  All calls are best-effort and
never raise.
"""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
from typing import Optional

_winmm = ctypes.WinDLL("winmm") if os.name == "nt" else None


class Sound:
    def __init__(self, winexe: Path) -> None:
        self.sounds_dir = winexe / "sounds"
        self.enabled = True

    def _play(self, path: Optional[Path]) -> None:
        if not self.enabled or not path or not _winmm or not path.exists():
            return
        try:
            alias = "bmsnd"
            _winmm.mciSendStringW(
                'open "%s" type waveaudio alias %s' % (str(path), alias), None, 0, None
            )
            _winmm.mciSendStringW("play %s" % alias, None, 0, None)
            _winmm.mciSendStringW("close %s" % alias, None, 0, None)
        except Exception:
            pass

    def _pick(self, prefix: str) -> Optional[Path]:
        if not self.sounds_dir.exists():
            return None
        files = sorted(self.sounds_dir.glob(prefix + "*.wav"))
        if not files:
            return None
        import random
        return random.choice(files)

    def win(self) -> None:
        self._play(self._pick("win"))

    def lose(self) -> None:
        self._play(self._pick("lose"))
