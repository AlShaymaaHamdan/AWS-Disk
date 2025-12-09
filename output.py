import sys
# from shared_jobs.Python.check_disk import check_disk
from check_disk import check_disk_usage

def main():
    if len(sys.argv) < 3:
        print("Usage: python check_disk_output.py <target> <drive_or_mount> [region]")
        sys.exit(1)

    target = sys.argv[1]
    drive_or_mount = sys.argv[2]
    region = sys.argv[3] if len(sys.argv) >= 4 else None

    try:
        # Run the check_disk function
        result = check_disk(target, drive_or_mount, region)

        # If check_disk prints internally, we can optionally format structured output
        print("✅ Disk check completed successfully!")
        print("------------------------------")
        # For structured output, we can print volume info and disk usage
        # Here assuming check_disk prints or returns volume_id and disk usage
        # If needed, modify check_disk.py to return these as a dict
    except Exception as e:
        print(f"❌ Disk check failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
