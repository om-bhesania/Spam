#!/usr/bin/env node
/**
 * main.js
 *
 * Moves the mouse to 2–3 random locations each cycle and simulates a key press.
 * No GUI, logs actions to terminal.
 *
 * Run only on machines you control.
 * Requires: npm install robotjs commander
 */

import robot from "robotjs";
import { Command } from "commander";

// ----------------- Defaults (edit here) -----------------
const INTERVAL_MIN = 3; // base minutes between cycles
const JITTER = 0.15; // ±fractional jitter
const MOVES_MIN = 1;
const MOVES_MAX = 2;
const PER_MOVE_DELAY = 1; // seconds between moves
const PRESS_EACH = false;
const KEY = "shift";
const MOVE_DURATION_RANGE = [80, 500]; // ms
const MARGIN = 5;
const DRY_RUN = false;
// ---------------------------------------------------------

let running = true;
process.on("SIGINT", () => {
  console.log("\nReceived SIGINT, shutting down...");
  running = false;
});
process.on("SIGTERM", () => {
  console.log("\nReceived SIGTERM, shutting down...");
  running = false;
});

const sleep = (ms) => new Promise((res) => setTimeout(res, ms));

function randomPosition(margin = MARGIN) {
  const { width, height } = robot.getScreenSize();
  const x = Math.floor(Math.random() * (width - 2 * margin)) + margin;
  const y = Math.floor(Math.random() * (height - 2 * margin)) + margin;
  return { x, y };
}

function chooseMovesCount(min, max) {
  if (min === max) return min;
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function computeNextWaitSeconds(baseMin, jitter) {
  const j = jitter > 0 ? (Math.random() * 2 - 1) * jitter : 0;
  return Math.max(0.1, baseMin * 60 * (1 + j));
}

async function moveMouseSmooth(x2, y2, durationMs) {
  const { x: x1, y: y1 } = robot.getMousePos();
  const steps = Math.max(10, Math.floor(durationMs / 10));
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    // Simple bezier-like curve
    const cx = (x1 + x2) / 2 + (Math.random() - 0.5) * 60;
    const cy = (y1 + y2) / 2 + (Math.random() - 0.5) * 60;
    const x =
      (1 - t) ** 2 * x1 +
      2 * (1 - t) * t * cx +
      t ** 2 * x2 +
      (Math.random() - 0.5) * 2;
    const y =
      (1 - t) ** 2 * y1 +
      2 * (1 - t) * t * cy +
      t ** 2 * y2 +
      (Math.random() - 0.5) * 2;
    robot.moveMouse(Math.round(x), Math.round(y));
    await sleep(durationMs / steps);
  }
}

async function pressKey(key) {
  try {
    robot.keyTap(key);
  } catch (err) {
    console.warn(`Failed to press '${key}': ${err}`);
  }
}

async function runLoop({
  baseInterval,
  jitter,
  minMoves,
  maxMoves,
  perMoveDelay,
  pressEach,
  key,
  dryRun,
}) {
  console.log(
    `STARTING: base_interval=${baseInterval}min, jitter=${jitter}, moves=${minMoves}-${maxMoves}, per_move_delay=${perMoveDelay}s, press_each=${pressEach}, key=${key}, dry_run=${dryRun}`
  );

  while (running) {
    const movesCount = chooseMovesCount(minMoves, maxMoves);
    console.log(`[${new Date().toLocaleString()}] Performing ${movesCount} move(s)...`);

    for (let i = 0; i < movesCount; i++) {
      const { x, y } = randomPosition();
      const dur = Math.random() * (MOVE_DURATION_RANGE[1] - MOVE_DURATION_RANGE[0]) + MOVE_DURATION_RANGE[0];
      if (dryRun) {
        console.log(`  DRY RUN -> move #${i + 1} to (${x},${y}) over ${dur.toFixed(0)}ms`);
      } else {
        await moveMouseSmooth(x, y, dur);
        console.log(`  Moved #${i + 1} -> (${x},${y}) over ${dur.toFixed(0)}ms`);
      }

      if (pressEach) {
        if (dryRun) console.log(`    DRY RUN -> would press '${key}'`);
        else {
          await pressKey(key);
          console.log(`    Pressed '${key}'`);
        }
      }

      if (i < movesCount - 1) {
        const end = Date.now() + perMoveDelay * 1000;
        while (running && Date.now() < end) await sleep(50);
      }
    }

    if (!pressEach) {
      if (dryRun) console.log(`  DRY RUN -> would press '${key}' after sequence`);
      else {
        await pressKey(key);
        console.log(`  Pressed '${key}' after sequence`);
      }
    }

    const waitSeconds = computeNextWaitSeconds(baseInterval, jitter);
    const nextTime = new Date(Date.now() + waitSeconds * 1000);
    console.log(`Next cycle at ~${nextTime.toLocaleTimeString()} (in ${(waitSeconds / 60).toFixed(2)} min).`);

    const end = Date.now() + waitSeconds * 1000;
    while (running && Date.now() < end) await sleep(200);
  }

  console.log("Exited loop. Bye.");
}

const program = new Command();
program
  .option("-m, --minutes <num>", "base interval in minutes", INTERVAL_MIN)
  .option("-j, --jitter <num>", "jitter fraction 0-1", JITTER)
  .option("--min-moves <num>", "minimum moves per cycle", MOVES_MIN)
  .option("--max-moves <num>", "maximum moves per cycle", MOVES_MAX)
  .option("-b, --between <num>", "seconds between moves", PER_MOVE_DELAY)
  .option("--press-each", "press key after each move")
  .option("--press-once", "press key once per cycle")
  .option("-k, --key <key>", "key to press", KEY)
  .option("--dry-run", "don’t move or press; only log");

program.parse(process.argv);
const opts = program.opts();

await runLoop({
  baseInterval: parseFloat(opts.minutes ?? INTERVAL_MIN),
  jitter: parseFloat(opts.jitter ?? JITTER),
  minMoves: parseInt(opts.minMoves ?? MOVES_MIN),
  maxMoves: parseInt(opts.maxMoves ?? MOVES_MAX),
  perMoveDelay: parseFloat(opts.between ?? PER_MOVE_DELAY),
  pressEach: opts.pressEach && !opts.pressOnce,
  key: opts.key ?? KEY,
  dryRun: !!opts.dryRun,
});
