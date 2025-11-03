#!/usr/bin/env python3
"""
main.py

Moves the mouse to 2-3 random locations each cycle and simulates a key press.
No prompts or GUI. Logs each action to the terminal.

Run only on machines you control.
Requires: pip install pyautogui
macOS: Terminal/Python must have Accessibility permission.
"""

import argparse
import logging
import random
import signal
import sys
import time
from typing import Tuple

try:
    import pyautogui
except Exception as exc:
    print("pyautogui is required. Install with: pip install pyautogui")
    raise SystemExit(1)


# --------------------- Default configuration (edit here) ---------------------
INTERVAL_MIN = 3            # base minutes between cycles
JITTER = 0.15                 # ±fractional jitter around INTERVAL_MIN (0.0 - 1.0)
MOVES_MIN = 1                 # minimum moves per cycle
MOVES_MAX = 2                 # maximum moves per cycle
PER_MOVE_DELAY = 1          # seconds between individual moves in a cycle
PRESS_EACH = False            # if True, press key after every move; else press once after the sequence
KEY = "shift"                 # pyautogui key name to press
MOVE_DURATION_RANGE = (0.08, 0.5)  # seconds to animate each move
MARGIN = 5                    # pixels margin from edges
DRY_RUN = False               # if True, only logs actions (no actual mouse/key)
# -----------------------------------------------------------------------------


# graceful shutdown flag
_running = True


def _handle_signal(signum, frame):
    global _running
    logging.info("Received signal %s, shutting down...", signum)
    _running = False


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


def random_position(margin: int = MARGIN) -> Tuple[int, int]:
    w, h = pyautogui.size()
    x = random.randint(margin, max(margin, w - margin - 1))
    y = random.randint(margin, max(margin, h - margin - 1))
    return x, y


def safe_press(key: str):
    try:
        pyautogui.press(key)
    except Exception as e:
        logging.warning("Failed to press '%s': %s", key, e)


def choose_moves_count(min_moves: int, max_moves: int) -> int:
    if min_moves == max_moves:
        return min_moves
    return random.randint(min_moves, max_moves)


def compute_next_wait_seconds(base_min: float, jitter: float) -> float:
    j = random.uniform(-jitter, jitter) if jitter > 0 else 0.0
    secs = max(0.1, (base_min * 60.0) * (1.0 + j))
    return secs


def run_loop(
    base_interval_min: float,
    jitter_pct: float,
    min_moves: int,
    max_moves: int,
    per_move_delay: float,
    press_each: bool,
    key: str,
    dry_run: bool,
):
    logging.info("STARTING: base_interval=%.2f min, jitter=%.2f, moves=%d-%d, per_move_delay=%.2fs, press_each=%s, key=%s, dry_run=%s",
                 base_interval_min, jitter_pct, min_moves, max_moves, per_move_delay, press_each, key, dry_run)
    global _running
    try:
        while _running:
            moves_count = choose_moves_count(min_moves, max_moves)
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            logging.info("[%s] Performing %d move(s) this cycle.", now, moves_count)

            for i in range(moves_count):
                x, y = random_position()
                dur = random.uniform(*MOVE_DURATION_RANGE)
                if dry_run:
                    logging.info("  DRY RUN -> move #%d to (%d,%d) over %.2fs", i + 1, x, y, dur)
                else:
                    try:
                        pyautogui.moveTo(x, y, duration=dur)
                        logging.info("  Moved #%d -> (%d,%d) over %.2fs", i + 1, x, y, dur)
                    except Exception as e:
                        logging.warning("  moveTo failed: %s", e)

                if press_each:
                    if dry_run:
                        logging.info("    DRY RUN -> would press '%s' after move #%d", key, i + 1)
                    else:
                        safe_press(key)
                        logging.info("    Pressed '%s' after move #%d", key, i + 1)

                # wait between moves if more remain
                if i < moves_count - 1:
                    sleep_left = per_move_delay
                    # small loop so we can react to shutdown signals during sleep
                    start_t = time.time()
                    while _running and (time.time() - start_t) < sleep_left:
                        time.sleep(0.05)

            if not press_each:
                if dry_run:
                    logging.info("  DRY RUN -> would press '%s' after sequence", key)
                else:
                    safe_press(key)
                    logging.info("  Pressed '%s' after sequence", key)

            # compute next wait
            wait_seconds = compute_next_wait_seconds(base_interval_min, jitter_pct)
            next_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + wait_seconds))
            logging.info("Next cycle at ~%s (in %.2f minutes).", next_ts, wait_seconds / 60.0)

            # sleep until next cycle, but remain responsive to signals
            start = time.time()
            while _running and (time.time() - start) < wait_seconds:
                time.sleep(0.2)

    except Exception as e:
        logging.exception("Unexpected error: %s", e)
    finally:
        logging.info("Exited run loop. Bye.")


def parse_cli_and_override_defaults():
    p = argparse.ArgumentParser(description="Random mouse mover - run without prompts (edit defaults in file or use flags).")
    p.add_argument("--minutes", "-m", type=float, help=f"Base interval in minutes (default {INTERVAL_MIN})")
    p.add_argument("--jitter", "-j", type=float, help=f"Jitter fraction 0-1 (default {JITTER})")
    p.add_argument("--min-moves", type=int, help=f"Minimum moves per cycle (default {MOVES_MIN})")
    p.add_argument("--max-moves", type=int, help=f"Maximum moves per cycle (default {MOVES_MAX})")
    p.add_argument("--between", "-b", type=float, help=f"Seconds between moves (default {PER_MOVE_DELAY})")
    p.add_argument("--press-each", action="store_true", help="Press the key after each move")
    p.add_argument("--press-once", action="store_true", help="Press the key once after the sequence (overrides --press-each)")
    p.add_argument("--key", "-k", type=str, help=f"Key to press (default '{KEY}')")
    p.add_argument("--dry-run", action="store_true", help="Don't move or press; only log actions")
    return p.parse_args()


def main():
    # logging setup: timestamped, simple to terminal
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    args = parse_cli_and_override_defaults()

    base_interval = args.minutes if args.minutes is not None else INTERVAL_MIN
    jitter = args.jitter if args.jitter is not None else JITTER
    min_moves = args.min_moves if args.min_moves is not None else MOVES_MIN
    max_moves = args.max_moves if args.max_moves is not None else MOVES_MAX
    per_move_delay = args.between if args.between is not None else PER_MOVE_DELAY
    press_each = args.press_each if args.press_each else (False if args.press_once else PRESS_EACH)
    key = args.key if args.key is not None else KEY
    dry_run = args.dry_run or DRY_RUN

    # validation
    if base_interval <= 0:
        logging.error("Base interval must be > 0.")
        sys.exit(1)
    if not (0.0 <= jitter <= 1.0):
        logging.error("Jitter must be between 0.0 and 1.0.")
        sys.exit(1)
    if min_moves < 1 or max_moves < min_moves:
        logging.error("Invalid move bounds: ensure 1 <= min_moves <= max_moves.")
        sys.exit(1)
    if per_move_delay < 0:
        logging.error("per_move_delay must be >= 0.")
        sys.exit(1)

    run_loop(
        base_interval_min=base_interval,
        jitter_pct=jitter,
        min_moves=min_moves,
        max_moves=max_moves,
        per_move_delay=per_move_delay,
        press_each=press_each,
        key=key,
        dry_run=dry_run,
    )


if __name__ == "__main__":
    main()
