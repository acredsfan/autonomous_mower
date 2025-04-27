# Copilot Custom Instructions for Autonomous Mower Project

## Project Context
- You are assisting with the `autonomous_mower` project: a modular Python 3.10+ robot mower running on Raspberry Pi 4B/5 with Bookworm OS.
- Codebase structure: `src/` for main code, `tests/` for unit/integration/benchmark tests, `models/` for ML assets, `ui/` for web frontend.
- Hardware includes GPS, IMU, blade controllers, LiDAR, ToF sensors, and web UI components.
- The goal is clean, modular, production-ready robotics software.

## Coding Style and Best Practices
- Python must follow PEP8, with line length <= 88 characters, using type hints.
- Use `snake_case` for Python, `camelCase` for JS.
- Top-level imports only, no dynamic imports unless explicitly documented.
- Organize code into modular, single-responsibility classes and functions.
- Default to readability and safety over code golf or cleverness.

## Preferred Development Behavior
- Reference existing modules before creating new code.
- Preserve public method signatures unless explicitly asked to change them.
- Log errors clearly, with enough context for hardware troubleshooting.
- Fail gracefully: if hardware is missing, fallback or warn, never crash.
- Validate `.env` files and environment variables before usage.

## Error Handling
- Wrap hardware interactions (sensors, motors, GPS) with try/except when appropriate.
- If critical models (e.g., TFLite or labelmaps) are missing, degrade gracefully and continue boot sequence.

## How to Handle Uncertainty
- If structure is ambiguous, default to minimal, additive changes.
- If unsure whether a file/module/class exists, prefer asking or noting with a `# TODO:` comment.
- Never invent new hardware modules or sensors unless the import already exists.

## Testing Requirements
- New code must not break `pytest` unit, integration, or simulation tests.
- Coverage target is `src/mower`, with pytest coverage >90% where practical.
- Mock hardware dependencies during testing when required.

## Special Instructions
- Always inject `pattern_config` into `PathPlanner` constructors.
- Launch the Web UI server immediately after successful hardware init.
- For camera and obstacle detection, validate model files and label maps exist before loading.
- Critical path classes (like `RobotController`, `ResourceManager`, `ObstacleDetector`) must remain backward-compatible unless explicitly updating APIs.

## AI Behavior Tuning
- Assume GPT-4.1's style: prioritize safe, modular, real-world maintainable code.
- Avoid hallucination or guessing about code structure or hardware.
- Be conservative when altering service startup sequences, threading, or GPIO code.

---
> Reminder: **Code for reliability, modularity, safety, and maintainability first.**
