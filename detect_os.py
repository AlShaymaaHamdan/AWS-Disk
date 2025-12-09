#!/usr/bin/env python3
import boto3
import sys
import time
import re

POLL_INTERVAL = 2
POLL_RETRIES = 30

def send_ssm_command(ssm_client, instance_id, command, is_windows):
    doc = "AWS-RunPowerShellScript" if is_windows else "AWS-RunShellScript"

    resp = ssm_client.send_command(
        InstanceIds=[instance_id],
        DocumentName=doc,
        Parameters={"commands": [command]},
    )
    cmd_id = resp["Command"]["CommandId"]

    for _ in range(POLL_RETRIES):
        time.sleep(POLL_INTERVAL)
        out = ssm_client.get_command_invocation(CommandId=cmd_id, InstanceId=instance_id)

        if out["Status"] in ("Success", "Failed", "Cancelled", "TimedOut"):
            return out

    print("SSM command timed out", file=sys.stderr)
    sys.exit(1)

def normalize_drive_windows(drive):
    d = drive.strip() # Trim whitespaces
    if len(d) == 1:
        return d.upper() + ":" # add : after windows drives ex. C:
    if d.endswith("\\") or d.endswith("/"):
        d = d[:-1] # remove trailing slashes
    if not d.endswith(":"):
        d = d.upper() + ":"
    return d

def parse_windows_output(output):
    m = re.search( # output will be like this: Drive:C: TotalGB:100 UsedGB:60 FreeGB:40 UsedPercent:60%
        r"TotalGB:([0-9\.]+)\s+UsedGB:([0-9\.]+)\s+FreeGB:([0-9\.]+)\s+UsedPercent:([0-9]+)%", 
        output
    )
    if not m:
        return None

    total, used, free, pct = m.groups() # Extract the four captured values
    return { # Return them as a dictionary
        "total": total,
        "used": used,
        "free": free,
        "pct": pct
    }


def parse_linux_output(output):
    """
    Parse 'df -h <mount>' output and extract:
    size, used, avail, percent, mount.

    Returns dict or None if not matched.
    """
    # Typical df -h line:
    # /dev/xvda1   10G   8G   2G   80%   /
    pattern = (
        r"(?P<filesystem>\S+)\s+"
        r"(?P<size>\S+)\s+"
        r"(?P<used>\S+)\s+"
        r"(?P<avail>\S+)\s+"
        r"(?P<pct>\d+)%\s+"
        r"(?P<mount>.+)"
    )

    m = re.search(pattern, output)
    if not m:
        return None

    return {
        "filesystem": m.group("filesystem"),
        "size": m.group("size"),
        "used": m.group("used"),
        "avail": m.group("avail"),
        "pct": m.group("pct"),
        "mount": m.group("mount").strip()
    }

def main():
    if len(sys.argv) != 4:
        print("Usage: python check_disk_usage.py <instance-id> <os-type> <drive-or-mount>", file=sys.stderr)
        sys.exit(1)

    instance_id = sys.argv[1].strip()
    os_type = sys.argv[2].strip().lower()
    drive = sys.argv[3].strip()
    region = sys.argv[4].strip()

    ssm = boto3.client("ssm", region_name=region)

    # WINDOWS
    if "win" in os_type:
        drive = normalize_drive_windows(drive)
        command = ( # Powershell Command that calculated data (total, free, used, percentage)
            f"$drv='{drive}'; "
            f"$ld=Get-CimInstance -ClassName Win32_LogicalDisk -Filter \"DeviceID='$drv'\"; "
            f"if(-not $ld){{ Write-Output \"DriveNotFound:$drv\"; exit 0 }}; "
            f"$sizeGB=[math]::Round($ld.Size/1GB,2); "
            f"$freeGB=[math]::Round($ld.FreeSpace/1GB,2); "
            f"$usedGB=[math]::Round($sizeGB - $freeGB,2); "
            f"$usedPct=[math]::Round((($sizeGB - $freeGB)/$sizeGB)*100,0); "
            f"Write-Output \"TotalGB:$sizeGB UsedGB:$usedGB FreeGB:$freeGB UsedPercent:$usedPct%\""
        )

        out = send_ssm_command(ssm, instance_id, command, is_windows=True)
        stdout = out.get("StandardOutputContent", "").strip()

        info = parse_windows_output(stdout)
        if not info:
            print("Could not parse Windows disk output.", file=sys.stderr)
            print(stdout)
            sys.exit(1)

        print(
            f"Drive {drive} | Total: {info['total']} GB | Used: {info['used']} GB | "
            f"Free: {info['free']} GB | UsedPercent: {info['pct']}%"
        )
        return

    # LINUX
    else:
        command = f"df -h {drive} | tail -1" # shell command
        out = send_ssm_command(ssm, instance_id, command, is_windows=False)
        stdout = out.get("StandardOutputContent", "").strip()

        info = parse_linux_output(stdout)
        if not info:
            print("Could not parse Linux disk output.", file=sys.stderr)
            print(stdout)
            sys.exit(1)

        print(
            f"Filesystem: {info['filesystem']} | Total: {info['size']} | "
            f"Used: {info['used']} | Free: {info['avail']} | "
            f"UsedPercent: {info['pct']}% | Mount: {info['mount']}"
        )


if __name__ == "__main__":
    main()
