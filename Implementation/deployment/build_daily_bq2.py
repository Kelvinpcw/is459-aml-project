"""Prepare an opt-in daily BQ2 route for the deployed main workflow."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re

from build_stack import ACCOUNT, BUCKET, REGION, allow, attr


MAIN = "is459-aml-full-pipeline"
MODE = "daily-bq2"
READY_PREFIX = "fresh-bq2/incoming/day="
READY_SUFFIX = "/ready.json"
DATE_PATTERN = r"/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/"
TIMESTAMP_PATTERN = r"/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/"
ETAG_PATTERN = r'/^"[0-9a-f]{32}(-[0-9]{1,5})?"$/'
CHILD_NAME = r"is459-aml-fresh-bq2-[a-z0-9][a-z0-9-]{0,19}"
CHILD_WAIT_SECONDS = 11_100


def daily_states(legacy_start: str, child_arn: str) -> dict:
    batch = "$states.input.batch_date"
    scheduled = "$states.input.scheduled_time"
    etag = "$states.input.ready.etag"
    return {
        "SelectWorkload": {
            "Type": "Choice",
            "Choices": [
                {"And": [{"Variable": "$.mode", "IsPresent": True},
                         {"Variable": "$.mode", "StringEquals": MODE}], "Next": "ResolveDailyBQ2Date"},
                {"And": [{"Variable": f"$.{field}", "IsPresent": False}
                         for field in ("mode", "batch_date", "scheduled_time")], "Next": legacy_start},
            ],
            "Default": "InvalidDailyBQ2Input",
        },
        "ResolveDailyBQ2Date": {
            "Type": "Choice", "QueryLanguage": "JSONata",
            "Choices": [
                {"Condition": f"{{% $type({batch}) = 'string' and $not($exists({scheduled})) %}}",
                 "Output": {"batch_date": "{% " + batch + " %}"}, "Next": "CheckDailyBQ2Date"},
                {"Condition": (f"{{% $not($exists({batch})) and $type({scheduled}) = 'string' and "
                               f"$exists($match($string({scheduled}), {TIMESTAMP_PATTERN})) %}}"),
                 "Output": {"batch_date": ("{% $fromMillis($toMillis(" + scheduled
                                           + ") - 86400000, '[Y0001]-[M01]-[D01]', '+0800') %}")},
                 "Next": "CheckDailyBQ2Date"},
            ],
            "Default": "InvalidDailyBQ2Input",
        },
        "CheckDailyBQ2Date": {
            "Type": "Choice", "QueryLanguage": "JSONata",
            "Choices": [{"Condition": f"{{% $exists($match({batch}, {DATE_PATTERN})) %}}",
                         "Next": "BuildDailyBQ2ReadyKey"}],
            "Default": "InvalidDailyBQ2Input",
        },
        "BuildDailyBQ2ReadyKey": {
            "Type": "Pass",
            "Parameters": {"batch_date.$": "$.batch_date",
                           "ready_key.$": f"States.Format('{READY_PREFIX}{{}}{READY_SUFFIX}', $.batch_date)"},
            "Next": "ReadDailyBQ2ReadyManifest",
        },
        "ReadDailyBQ2ReadyManifest": {
            "Type": "Task", "Resource": "arn:aws:states:::aws-sdk:s3:getObject",
            "Parameters": {"Bucket": BUCKET, "ExpectedBucketOwner": ACCOUNT, "Key.$": "$.ready_key",
                           "Range": "bytes=0-65535"},
            "ResultSelector": {"manifest.$": "States.StringToJson($.Body)", "etag.$": "$.ETag"},
            "ResultPath": "$.ready", "Next": "CheckDailyBQ2Manifest",
        },
        "CheckDailyBQ2Manifest": {
            "Type": "Choice", "QueryLanguage": "JSONata",
            "Choices": [{"Condition": ("{% $states.input.ready.manifest.schema_version = 1 and "
                                       f"$states.input.ready.manifest.batch_start = {batch} and "
                                       f"$exists($match({etag}, {ETAG_PATTERN})) %}}"),
                         "Next": "BuildDailyBQ2ChildInput"}],
            "Default": "InvalidDailyBQ2Manifest",
        },
        "BuildDailyBQ2ChildInput": {
            "Type": "Pass", "QueryLanguage": "JSONata",
            "Output": {"ready_key": "{% $states.input.ready_key %}",
                       "ready_etag": f"{{% $replace({etag}, /\"/, '') %}}",
                       "attempt_id": f"{{% '{MODE}-' & {batch} & '-' & $replace({etag}, /\"/, '') %}}"},
            "Next": "RunDailyBQ2",
        },
        "RunDailyBQ2": {
            "Type": "Task", "Resource": "arn:aws:states:::states:startExecution.sync:2",
            "Parameters": {"StateMachineArn": child_arn, "Name.$": "$.attempt_id", "Input.$": "$"},
            "TimeoutSeconds": CHILD_WAIT_SECONDS,
            "End": True,
        },
        "InvalidDailyBQ2Input": {
            "Type": "Fail", "Error": "InvalidDailyBQ2Input",
            "Cause": "Use daily-bq2 mode with one YYYY-MM-DD batch_date or a Scheduler scheduled_time.",
        },
        "InvalidDailyBQ2Manifest": {
            "Type": "Fail", "Error": "InvalidDailyBQ2Manifest",
            "Cause": "The ready manifest must use schema 1, match the selected batch date and have a valid S3 ETag.",
        },
    }


def build(base: dict, child_name: str) -> dict:
    if not re.fullmatch(CHILD_NAME, child_name):
        raise ValueError("Supply the name of the reviewed fresh BQ2 workflow in the project account")

    template = deepcopy(base)
    resources = template["Resources"]
    workflow = resources["Workflow"]["Properties"]
    if (workflow["StateMachineName"] != MAIN or workflow["StateMachineType"] != "STANDARD"
            or workflow["RoleArn"] != attr("WorkflowRole", "Arn")):
        raise ValueError("Expected the project main Standard workflow and its existing execution role")
    definition_slot = workflow["DefinitionString"]["Fn::Sub"]
    definition = json.loads(definition_slot[0])
    if definition.get("QueryLanguage", "JSONPath") != "JSONPath":
        raise ValueError("The main workflow must use JSONPath before adding the daily route")
    child_arn = f"arn:aws:states:{REGION}:{ACCOUNT}:stateMachine:{child_name}"
    execution_arn = f"arn:aws:states:{REGION}:{ACCOUNT}:execution:{child_name}:{MODE}-*"
    added = daily_states(definition["StartAt"], child_arn)
    if added.keys() & definition["States"].keys():
        raise ValueError("Daily BQ2 already exists in this template")
    definition["States"] = {**added, **definition["States"]}
    definition["StartAt"] = "SelectWorkload"
    definition_slot[0] = json.dumps(definition)

    policy = {"Version": "2012-10-17", "Statement": [
        allow("s3:GetObject", f"arn:aws:s3:::{BUCKET}/{READY_PREFIX}*{READY_SUFFIX}"),
        allow("states:StartExecution", child_arn),
        allow(["states:DescribeExecution", "states:StopExecution"], execution_arn),
        allow(["events:PutRule", "events:PutTargets", "events:DescribeRule"],
              f"arn:aws:events:{REGION}:{ACCOUNT}:rule/StepFunctionsGetEventsForStepFunctionsExecutionRule"),
    ]}
    resources["WorkflowRole"]["Properties"]["Policies"].append(
        {"PolicyName": "RunDailyBQ2", "PolicyDocument": policy})

    return template


def retarget(base: dict, old_child: str, new_child: str) -> dict:
    """Replace the reviewed child target and widen only its synchronous wait."""
    if (not re.fullmatch(CHILD_NAME, old_child) or not re.fullmatch(CHILD_NAME, new_child)
            or old_child == new_child):
        raise ValueError("Supply distinct reviewed fresh BQ2 workflow names")
    template = deepcopy(base)
    resources = template["Resources"]
    workflow = resources["Workflow"]["Properties"]
    if workflow["StateMachineName"] != MAIN or workflow["RoleArn"] != attr("WorkflowRole", "Arn"):
        raise ValueError("Require the project main workflow and its execution role")
    slot = workflow["DefinitionString"]["Fn::Sub"]
    definition = json.loads(slot[0])
    task = definition["States"]["RunDailyBQ2"]
    old_state_machine = f"arn:aws:states:{REGION}:{ACCOUNT}:stateMachine:{old_child}"
    new_state_machine = f"arn:aws:states:{REGION}:{ACCOUNT}:stateMachine:{new_child}"
    old_execution = f"arn:aws:states:{REGION}:{ACCOUNT}:execution:{old_child}:{MODE}-*"
    new_execution = f"arn:aws:states:{REGION}:{ACCOUNT}:execution:{new_child}:{MODE}-*"
    if (definition["StartAt"] != "SelectWorkload" or task["Resource"] != "arn:aws:states:::states:startExecution.sync:2"
            or task["Parameters"]["StateMachineArn"] != old_state_machine
            or definition["TimeoutSeconds"] <= CHILD_WAIT_SECONDS):
        raise ValueError("Main workflow is not the reviewed daily BQ2 route")
    policy, = [entry["PolicyDocument"] for entry in resources["WorkflowRole"]["Properties"]["Policies"]
               if entry["PolicyName"] == "RunDailyBQ2"]
    for action, previous, updated in (("states:StartExecution", old_state_machine, new_state_machine),
                                      (["states:DescribeExecution", "states:StopExecution"], old_execution, new_execution)):
        statement, = [item for item in policy["Statement"] if item == allow(action, previous)]
        statement["Resource"] = updated
    task["Parameters"]["StateMachineArn"] = new_state_machine
    task["TimeoutSeconds"] = CHILD_WAIT_SECONDS
    slot[0] = json.dumps(definition)
    return template


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-template", required=True, type=Path)
    parser.add_argument("--child-name", required=True)
    parser.add_argument("--replace-child-name")
    args = parser.parse_args()
    base = json.loads(args.main_template.read_bytes())
    template = (retarget(base, args.replace_child_name, args.child_name)
                if args.replace_child_name else build(base, args.child_name))
    # Keep the reviewed main stack within CloudFormation's 51,200-byte inline template limit.
    print(json.dumps(template, indent=1))
