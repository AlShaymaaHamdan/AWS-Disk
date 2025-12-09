import boto3
import re
import sys

def resolve_instance_id(ec2, target):
    """
    Resolve an instance by:
    - Instance ID
    - Private IP
    - Public IP
    - tag:Name
    - tag:Hostname
    Returns the instance ID or raises ValueError.
    """

    # Case 1: looks like an instance ID
    import re
    if re.fullmatch(r"i-[0-9a-f]{8,}", target): #instance id is i-123456habcdef 
        try:
            resp = ec2.describe_instances(InstanceIds=[target]) #validate if this id actually exists on AWS
            if resp.get("Reservations"): # Will return a reservation in AWS if the id exists
                return target
        except Exception:
            pass

    # Build filters for all other possibilities
    filters = [
        {"Name": "private-ip-address", "Values": [target]},
        {"Name": "ip-address", "Values": [target]},
        {"Name": "tag:Name", "Values": [target]},
        {"Name": "tag:Hostname", "Values": [target]},
    ]

    for f in filters:
        try:
            resp = ec2.describe_instances(Filters=[f])
            res = resp.get("Reservations", [])

            # Case: exactly one instance
            if len(res) == 1 and len(res[0]["Instances"]) == 1:
                return res[0]["Instances"][0]["InstanceId"]

            # Case: multiple matches
            if len(res) > 1:
                raise ValueError(
                    f"Identifier '{target}' matches multiple instances. "
                )

        except Exception:
            # Ignore AWS and try next filter
            pass

    # Zero matches after trying everything
    raise ValueError(
        f"No instance matches '{target}'. "
    )

