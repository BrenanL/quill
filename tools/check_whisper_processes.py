#!/usr/bin/env python3
"""
Check for running Whisper/pytest processes and optionally terminate them.

Detects:
- pytest processes running whisper tests
- Python processes with whisper/faster-whisper imported
- Python processes using GPU memory
- Running Quill application

Usage:
    python tools/check_whisper_processes.py           # Check and ask to kill
    python tools/check_whisper_processes.py --kill    # Auto-kill (SIGTERM)
    python tools/check_whisper_processes.py --force   # Force kill (SIGKILL)
"""

import sys
import os
import argparse
import subprocess
import signal


class ProcessInfo:
    """Container for process information."""
    def __init__(self, pid, cmd, cpu, ram, vram=0, status="unknown"):
        self.pid = pid
        self.cmd = cmd
        self.cpu = cpu
        self.ram = ram
        self.vram = vram
        self.status = status

    def __str__(self):
        vram_str = f"VRAM: {self.vram} MB | " if self.vram > 0 else ""
        return (f"PID: {self.pid} | CPU: {self.cpu}% | RAM: {self.ram} MB | {vram_str}"
                f"Status: {self.status}\n    Command: {self.cmd}")


def find_processes_by_pattern():
    """Find Python processes matching Whisper/pytest patterns."""
    processes = []

    try:
        # Use ps to find Python processes
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return processes

        # Parse ps output
        for line in result.stdout.split('\n')[1:]:  # Skip header
            if not line.strip():
                continue

            parts = line.split(None, 10)  # Split into max 11 parts
            if len(parts) < 11:
                continue

            user, pid, cpu, mem, vsz, rss, tty, stat, start, time, cmd = parts

            # Skip this script itself
            if 'check_whisper_processes.py' in cmd:
                continue

            # Check if it's a Python process with relevant keywords
            cmd_lower = cmd.lower()
            if 'python' not in cmd_lower:
                continue

            # Check for patterns
            is_match = False
            if 'pytest' in cmd_lower and 'whisper' in cmd_lower:
                is_match = True
            elif 'whisper' in cmd_lower or 'faster-whisper' in cmd_lower or 'faster_whisper' in cmd_lower:
                is_match = True
            elif 'quill' in cmd_lower and ('-m quill' in cmd_lower or '__main__.py' in cmd_lower):
                is_match = True

            if is_match:
                # Calculate RAM in MB (RSS is in KB on most systems)
                ram_mb = int(rss) / 1024 if rss.isdigit() else 0

                process = ProcessInfo(
                    pid=int(pid),
                    cmd=cmd,
                    cpu=float(cpu) if cpu.replace('.', '').isdigit() else 0.0,
                    ram=int(ram_mb),
                    status=stat
                )
                processes.append(process)

    except Exception as e:
        print(f"Error finding processes: {e}", file=sys.stderr)

    return processes


def find_gpu_processes():
    """Find Python processes using GPU memory via nvidia-smi."""
    gpu_usage = {}

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,used_memory",
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                parts = line.split(',')
                if len(parts) >= 2:
                    pid = int(parts[0].strip())
                    vram = int(parts[1].strip())
                    gpu_usage[pid] = vram

    except (FileNotFoundError, subprocess.TimeoutExpired):
        # nvidia-smi not available or timed out
        pass
    except Exception as e:
        print(f"Warning: Could not query GPU processes: {e}", file=sys.stderr)

    return gpu_usage


def enrich_with_gpu_info(processes):
    """Add GPU memory info to processes."""
    gpu_usage = find_gpu_processes()

    for proc in processes:
        if proc.pid in gpu_usage:
            proc.vram = gpu_usage[proc.pid]

    return processes


def kill_processes(processes, force=False):
    """Kill the given processes."""
    sig = signal.SIGKILL if force else signal.SIGTERM
    sig_name = "SIGKILL" if force else "SIGTERM"

    killed = []
    failed = []

    for proc in processes:
        try:
            os.kill(proc.pid, sig)
            killed.append(proc.pid)
            print(f"  ✓ Killed PID {proc.pid} ({sig_name})")
        except ProcessLookupError:
            print(f"  - PID {proc.pid} already terminated")
        except PermissionError:
            print(f"  ✗ Permission denied for PID {proc.pid}")
            failed.append(proc.pid)
        except Exception as e:
            print(f"  ✗ Failed to kill PID {proc.pid}: {e}")
            failed.append(proc.pid)

    return killed, failed


def clear_gpu_cache():
    """Clear CUDA cache after killing processes."""
    try:
        import torch
        import gc

        if torch.cuda.is_available():
            gc.collect()
            torch.cuda.empty_cache()
            print("\n  ✓ GPU cache cleared")
            return True
        else:
            print("\n  - No CUDA GPU available")
            return False
    except ImportError:
        print("\n  - PyTorch not available, cannot clear GPU cache")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Check for running Whisper/pytest processes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check for processes (interactive)
  python tools/check_whisper_processes.py

  # Auto-kill processes with SIGTERM
  python tools/check_whisper_processes.py --kill

  # Force kill with SIGKILL
  python tools/check_whisper_processes.py --force
        """
    )

    parser.add_argument(
        '--kill',
        action='store_true',
        help='Automatically kill found processes (SIGTERM)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force kill with SIGKILL instead of SIGTERM'
    )

    args = parser.parse_args()

    # Force implies kill
    if args.force:
        args.kill = True

    print("=" * 70)
    print("Whisper Process Checker")
    print("=" * 70)
    print("\nSearching for Whisper/pytest processes...\n")

    # Find processes
    processes = find_processes_by_pattern()

    if not processes:
        print("✓ No Whisper-related processes found")
        print("\nChecking GPU memory...")

        # Still check if GPU has memory allocated
        gpu_usage = find_gpu_processes()
        if gpu_usage:
            print(f"  Warning: Found {len(gpu_usage)} process(es) using GPU:")
            for pid, vram in gpu_usage.items():
                print(f"    PID {pid}: {vram} MB VRAM")
                try:
                    # Try to get process name
                    result = subprocess.run(
                        ["ps", "-p", str(pid), "-o", "comm="],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        print(f"      ({result.stdout.strip()})")
                except:
                    pass
        else:
            print("  ✓ No GPU processes found")

        sys.exit(0)

    # Enrich with GPU info
    processes = enrich_with_gpu_info(processes)

    # Display found processes
    print(f"Found {len(processes)} Whisper-related process(es):\n")

    for i, proc in enumerate(processes, 1):
        print(f"[{i}] {proc}\n")

    # Calculate totals
    total_ram = sum(p.ram for p in processes)
    total_vram = sum(p.vram for p in processes)

    print(f"Total: {total_ram} MB RAM", end="")
    if total_vram > 0:
        print(f", {total_vram} MB VRAM", end="")
    print("\n")

    # Decide whether to kill
    should_kill = False

    if args.kill:
        should_kill = True
        print("Auto-kill enabled")
    else:
        # Ask user
        response = input("Kill these processes? (y/n): ").strip().lower()
        should_kill = response in ('y', 'yes')

    if should_kill:
        print(f"\nKilling processes with {'SIGKILL' if args.force else 'SIGTERM'}...\n")

        killed, failed = kill_processes(processes, force=args.force)

        print(f"\nResults:")
        print(f"  Killed: {len(killed)}")
        print(f"  Failed: {len(failed)}")

        if killed:
            # Clear GPU cache
            clear_gpu_cache()

        if failed:
            print(f"\nWarning: {len(failed)} process(es) could not be killed")
            sys.exit(1)
        else:
            print("\n✓ All processes terminated successfully")
            sys.exit(0)
    else:
        print("Aborted - no processes killed")
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
