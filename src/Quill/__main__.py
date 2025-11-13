"""Quill entry point."""

import sys
from pathlib import Path

from .app import QuillApp


def main():
    """Main entry point for Quill."""
    # Find config
    config_path = Path("config.yaml")

    if not config_path.exists():
        print("WARNING: config.yaml not found")
        print("Creating from config.example.yaml...")

        example_path = Path("config.example.yaml")
        if example_path.exists():
            import shutil
            shutil.copy(example_path, config_path)
            print(f"Created {config_path}")
        else:
            print("ERROR: config.example.yaml not found")
            print("Please create config.yaml from the example")
            sys.exit(1)

    try:
        # Create and start app
        app = QuillApp(config_path)
        app.start()  # Blocking

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
