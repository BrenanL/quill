#!/usr/bin/env python3
"""
Check if Whisper model is loaded in memory (GPU VRAM or CPU RAM).

Usage:
    python tools/check_whisper_memory.py
    python tools/check_whisper_memory.py --clear-cache
"""

import sys
import gc
import argparse


def check_cuda_memory():
    """Check CUDA GPU memory usage."""
    try:
        import torch
    except ImportError:
        print("PyTorch not installed - cannot check CUDA memory")
        return None

    if not torch.cuda.is_available():
        print("CUDA not available - models running on CPU")
        return None

    allocated = torch.cuda.memory_allocated() / 1024**3
    reserved = torch.cuda.memory_reserved() / 1024**3

    print(f"CUDA Memory:")
    print(f"  Allocated: {allocated:.2f} GB")
    print(f"  Reserved:  {reserved:.2f} GB")

    return {"allocated": allocated, "reserved": reserved}


def check_system_memory():
    """Check system RAM usage."""
    try:
        import psutil
    except ImportError:
        print("psutil not installed - cannot check system memory")
        print("Install: pip install psutil")
        return None

    mem = psutil.virtual_memory()
    print(f"\nSystem Memory:")
    print(f"  Total:     {mem.total / 1024**3:.2f} GB")
    print(f"  Used:      {mem.used / 1024**3:.2f} GB ({mem.percent:.1f}%)")
    print(f"  Available: {mem.available / 1024**3:.2f} GB")

    return mem


def check_gpu_processes():
    """Check which processes are using the GPU."""
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
             "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0 and result.stdout.strip():
            print(f"\nGPU Processes:")
            for line in result.stdout.strip().split('\n'):
                print(f"  {line}")
            return result.stdout
        else:
            print(f"\nGPU Processes: None")
            return None
    except FileNotFoundError:
        print("\nnvidia-smi not found - cannot check GPU processes")
        return None
    except Exception as e:
        print(f"\nError checking GPU processes: {e}")
        return None


def clear_cache():
    """Force garbage collection and clear CUDA cache."""
    print("Clearing cache...")

    # Force garbage collection
    gc.collect()
    print("  ✓ Python garbage collection complete")

    # Clear CUDA cache if available
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            print("  ✓ CUDA cache cleared")
        else:
            print("  - CUDA not available (CPU only)")
    except ImportError:
        print("  - PyTorch not available")

    print("\nMemory after clearing:")
    check_cuda_memory()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Check if Whisper model is loaded in memory"
    )
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Clear CUDA cache and force garbage collection'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Whisper Memory Check")
    print("=" * 60)

    if args.clear_cache:
        clear_cache()
    else:
        # Check CUDA memory
        check_cuda_memory()

        # Check system memory
        check_system_memory()

        # Check GPU processes
        check_gpu_processes()

        print("\n" + "=" * 60)
        print("\nTo clear cache: python tools/check_whisper_memory.py --clear-cache")


if __name__ == "__main__":
    main()
