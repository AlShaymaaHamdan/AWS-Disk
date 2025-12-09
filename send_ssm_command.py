import boto3
from wait_for_status import wait_for_ssm_command

def send_ssm_command(ssm_client, instance_id, command, is_windows=False):
    doc_name = "AWS-RunPowerShellScript" if is_windows else "AWS-RunShellScript"

    response = ssm_client.send_command(
        InstanceIds=[instance_id],
        DocumentName=doc_name,
        Parameters={"commands": [command]},
    )

    command_id = response["Command"]["CommandId"]

    # Extract region from client so we don't touch your precious waiter
    region = ssm_client.meta.region_name

    return wait_for_ssm_command(command_id, region)
