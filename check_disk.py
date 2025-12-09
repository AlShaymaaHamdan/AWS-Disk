import boto3
from resolve_instance_id import resolve_instance_id
from detect_os import detect_os
from send_ssm_command import send_ssm_command
from find_EBS_vol import find_volume_for_drive


def check_disk_usage(target, drive="/", region=None):
    """
    Check disk usage on an EC2 instance and find the linked EBS volume.

    Returns:
        dict with disk usage and volume id
    """

    ec2 = boto3.client("ec2", region_name=region) if region else boto3.client("ec2")
    ssm = boto3.client("ssm", region_name=region) if region else boto3.client("ssm")

    # 1.Resolve instance ID
    instance_id = resolve_instance_id(ec2, target)

    # 2. Detect OS
    platform = detect_os(instance_id, region)

    # 3. Build OS-specific disk check command
    if "win" in platform.lower():
        drive_letter = drive.strip(":")
        cmd = (
            f"$d = Get-Volume -DriveLetter {drive_letter}; "
            f"$used = ($d.Size - $d.SizeRemaining); "
            f"$total = $d.Size; "
            f"$percent = [math]::Round(($used / $total) * 100,2); "
            f'Write-Output "$percent,$([math]::Round($used/1GB,2)),$([math]::Round($total/1GB,2))"'
        )
        is_windows = True
    else:
        cmd = (
            f"df -BG {drive} | tail -1 | "
            "awk '{print $3\",\"$2\",\"$5}' | tr -d 'G%'"
        )
        is_windows = False

    # 4. Run SSM command for disk usage
    resp = send_ssm_command(ssm, instance_id, cmd, is_windows=is_windows)
    output = resp["StandardOutputContent"].strip()

    # 5. Parse output
    try:
        if is_windows:
            used_pct, used_gb, total_gb = output.split(",")
        else:
            used_gb, total_gb, used_pct = output.split(",")
    except Exception:
        raise RuntimeError(f"Failed to parse disk usage output: {output}")

    # 6. Find matching EBS volume
    volume_id = find_volume_for_drive(ec2, instance_id, platform, drive)

    # 7. Result object
    result = {
        "InstanceId": instance_id,
        "Platform": platform,
        "Drive": drive,
        "UsedPercent": float(used_pct),
        "UsedGB": float(used_gb),
        "TotalGB": float(total_gb),
        "VolumeId": volume_id,
    }

    # 8. Print volume ID (because you asked for noise)
    print(f" EBS Volume ID for {drive} on {instance_id}: {volume_id}")

    return result
