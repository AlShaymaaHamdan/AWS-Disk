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

    region = ssm_client.meta.region_name

    wait_for_ssm_command(command_id, region)

    # now fetch output manually
    time.sleep(2)

    resp = ssm_client.list_command_invocations(
        CommandId=command_id,
        InstanceId=instance_id,
        Details=True
    )

    invocation = resp["CommandInvocations"][0]
    plugin = invocation["CommandPlugins"][0]

    return {
        "Status": invocation["Status"],
        "StandardOutputContent": plugin.get("Output", "")
    }
