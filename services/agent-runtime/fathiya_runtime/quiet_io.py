from __future__ import annotations

import os
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from typing import Iterator


@contextmanager
def quiet_huggingface_output() -> Iterator[None]:
    """Keep HF progress/warnings away from fragile service stdout handles."""
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    with open(os.devnull, "w", encoding="utf-8") as sink:
        with redirect_stdout(sink), redirect_stderr(sink):
            try:
                from huggingface_hub.utils import disable_progress_bars

                disable_progress_bars()
            except Exception:
                pass
            yield
