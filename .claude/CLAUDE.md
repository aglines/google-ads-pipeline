# CLAUDE.md

## Session Continuity

**At the start of each session**, check the date to be sure you know the real exact current date, state that date, and then read `.claude/curr-session.md` for the items we will store in every log, which are:
- The date of this session
- Where we left off last time, generally speaking
- Ongoing primary assumptions and decisions
- Decisions made in the most recent session and their rationale
- Current blockers or open questions
- Planned next steps

**At the end of each session** (or when asked), check to see if there is currently a log file with today's date. If so, append the most recent items we have worked on into that file.  If there is not yet today's date, copy `.claude/curr-session.md` into a file `.claude/log-[DATE].md`. Include the current date, and the items we store in every log.

**Never delete a log file.  Do not overwrite a log file, only append items to it**

---

## Python Environment

This project uses **uv** for Python project and dependency management.

### Required practices:
- Always use `uv run` to execute Python scripts (e.g., `uv run python script.py`)
- Use `uv add <package>` to add dependencies, never `pip install`
- Use `uv sync` to synchronize the environment from pyproject.toml
- Use `uv run pytest` for tests, `uv run mypy` for type checking, etc.
- Never activate virtual environments manually; `uv run` handles this
- If creating a new project, use `uv init`
