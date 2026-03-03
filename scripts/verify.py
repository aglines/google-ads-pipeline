#!/usr/bin/env python3
"""Run phase verification tests and save results to reports/.

Usage:
    uv run scripts/verify.py [phase]

Examples:
    uv run scripts/verify.py 1        # Run phase 1 verification
    uv run scripts/verify.py all      # Run all phase verifications
    uv run scripts/verify.py          # Same as 'all'
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_verification(phase: str | None = None) -> int:
    """Run verification tests and save results."""
    project_root = Path(__file__).parent.parent
    reports_dir = project_root / "reports"
    reports_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    if phase and phase != "all":
        test_paths = [f"tests/verify_phase{phase}.py"]
        report_name = f"phase{phase}_{timestamp}"
    else:
        # Explicitly list all verify_phase*.py files
        test_paths = [f"tests/verify_phase{i}.py" for i in range(11)]
        report_name = f"all_{timestamp}"

    xml_report = reports_dir / f"{report_name}.xml"
    log_report = reports_dir / f"{report_name}.log"

    cmd = [
        "uv",
        "run",
        "pytest",
        *test_paths,
        "-v",
        f"--junitxml={xml_report}",
    ]

    print(f"Running: {' '.join(cmd)}")
    print(f"XML report: {xml_report}")
    print(f"Log report: {log_report}")
    print("-" * 60)

    with open(log_report, "w") as log_file:
        log_file.write(f"Verification run: {timestamp}\n")
        log_file.write(f"Command: {' '.join(cmd)}\n")
        log_file.write("=" * 60 + "\n\n")

        result = subprocess.run(
            cmd,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        print(result.stdout)
        log_file.write(result.stdout)

        log_file.write("\n" + "=" * 60 + "\n")
        log_file.write(f"Exit code: {result.returncode}\n")

    # Create/update latest symlink
    latest_xml = (
        reports_dir / f"latest_phase{phase if phase and phase != 'all' else 'all'}.xml"
    )
    latest_log = (
        reports_dir / f"latest_phase{phase if phase and phase != 'all' else 'all'}.log"
    )

    if latest_xml.is_symlink():
        latest_xml.unlink()
    if latest_log.is_symlink():
        latest_log.unlink()

    latest_xml.symlink_to(xml_report.name)
    latest_log.symlink_to(log_report.name)

    return result.returncode


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"

    if phase not in ["all", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]:
        print(f"Invalid phase: {phase}")
        print("Valid phases: 0-10, all")
        sys.exit(1)

    exit_code = run_verification(phase)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
