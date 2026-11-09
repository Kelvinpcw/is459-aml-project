"""Generate the isolated fresh BQ2 smoke stack for review."""

import json

from build_stack import ACCOUNT, BUCKET, REGION, allow, attr, ref, sub, trust


STAGES = {
    "Prepare": "prepare",
    "Detect": "detect",
    "ScoreAndRank": "score",
    "Evaluate": "evaluate",
    "Publish": "publish",
}
WORKERS = 2
TIMEOUT_MINUTES = 10
NAMESPACE = "is459-aml-fresh-bq2-${DeploymentId}"
CODE = "fresh-bq2/code/${CodeVersion}/"
MODELS = "fresh-bq2/models/${ModelBundleId}/"
INCOMING = "fresh-bq2/incoming/*"
READY = "fresh-bq2/incoming/*/ready.json"
REFERENCE = "fresh-bq2/reference/*"
FACTS = "curated/dataset_version=fresh-bq2-*/run_id=*/transactions/*"
CASES = "gold/cases/dataset_version=fresh-bq2-*/run_id=*/analysis_id=fresh-bq2-v1/*"
RELEASES = "published/bq2/*"
RELEASE_POINTER = "published/bq2/current.json"
RELEASE_MANIFEST = "published/bq2/*/release.json"
STAGED = {stage: f"fresh-bq2/runs/*/{stage}/*" for stage in STAGES.values()}


def workflow_definition() -> dict:
    fields = ("ready_key", "ready_etag", "attempt_id")
    states = {
        "CheckReadyInput": {
            "Type": "Choice",
            "Choices": [{
                "And": [
                    *({"Variable": f"$.{field}", "IsString": True} for field in fields),
                    {"Variable": "$.ready_key", "StringMatches": READY},
                ],
                "Next": "Prepare",
            }],
            "Default": "InvalidInput",
        },
        "InvalidInput": {"Type": "Fail", "Error": "InvalidReadyInput",
                         "Cause": "Supply the ready manifest key, ETag and a unique attempt ID."},
    }
    names = list(STAGES)
    for index, name in enumerate(names):
        state = {
            "Type": "Task",
            "Resource": "arn:aws:states:::glue:startJobRun.sync",
            "Parameters": {
                "JobName": "${" + name + "Job}",
                "Arguments": {f"--{field.replace('_', '-')}.$": f"$.{field}" for field in fields},
            },
            "ResultPath": None,
        }
        if index + 1 < len(names):
            state["Next"] = names[index + 1]
        else:
            state["End"] = True
        states[name] = state
    return {
        "Comment": "Process one explicitly identified BQ2 batch and publish after validation.",
        "StartAt": "CheckReadyInput",
        "TimeoutSeconds": 3600,
        "States": states,
    }


def glue_role(stage: str, read_paths: list[str], write_paths: list[str], log_prefix: str) -> dict:
    bucket_arn = f"arn:aws:s3:::{BUCKET}"
    read = [READY, RELEASE_POINTER, RELEASE_MANIFEST, CODE + "*", *read_paths, *write_paths]
    temp = f"fresh-bq2/temp/${{DeploymentId}}/{stage}/*"
    logs = f"arn:aws:logs:{REGION}:{ACCOUNT}:log-group:{log_prefix}"
    policies = [
        allow("s3:GetBucketLocation", bucket_arn),
        {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": bucket_arn,
            "Condition": {"StringLike": {"s3:prefix": [RELEASE_POINTER, sub(temp), sub(temp[:-1])]}}
        },
        allow("s3:GetObject", [sub(f"{bucket_arn}/{path}") for path in read + [temp]]),
        allow("s3:PutObject", [sub(f"{bucket_arn}/{path}") for path in write_paths + [temp]]),
        allow(["s3:DeleteObject", "s3:AbortMultipartUpload"], sub(f"{bucket_arn}/{temp}")),
        allow("logs:CreateLogGroup", [sub(f"{logs}/{channel}") for channel in ("error", "output")]),
        allow(
            ["logs:CreateLogStream", "logs:PutLogEvents"],
            [sub(f"{logs}/{channel}:log-stream:*") for channel in ("error", "output")],
        ),
    ]
    if stage in ("prepare", "detect", "score"):
        private = [REFERENCE, "references/*", STAGED["evaluate"],
                   "quality/evaluation/*", "published/bq2/*/evaluation.json"]
        policies.append({
            "Effect": "Deny",
            "Action": ["s3:GetObject", "s3:GetObjectVersion"],
            "Resource": [f"{bucket_arn}/{path}" for path in private],
        })
    return {
        "Type": "AWS::IAM::Role",
        "Properties": {
            "RoleName": sub(f"{NAMESPACE}-{stage}"),
            "AssumeRolePolicyDocument": trust("glue.amazonaws.com"),
            "Policies": [{
                "PolicyName": "FreshBQ2Stage",
                "PolicyDocument": {"Version": "2012-10-17", "Statement": policies},
            }],
        },
    }


def build() -> dict:
    s3 = f"s3://{BUCKET}/"
    state_machine_arn = f"arn:aws:states:{REGION}:{ACCOUNT}:stateMachine:{NAMESPACE}"
    trigger_arn = f"arn:aws:events:{REGION}:{ACCOUNT}:rule:{NAMESPACE}-ready"
    access = {
        "prepare": ([INCOMING], [FACTS, STAGED["prepare"]]),
        "detect": ([STAGED["prepare"], FACTS], [CASES, STAGED["detect"]]),
        "score": ([STAGED["prepare"], STAGED["detect"], FACTS, CASES, MODELS + "*"], [STAGED["score"]]),
        "evaluate": ([STAGED["prepare"], STAGED["detect"], STAGED["score"], FACTS, CASES, REFERENCE],
                     [STAGED["evaluate"]]),
        "publish": ([STAGED["detect"], STAGED["score"], STAGED["evaluate"], CASES, RELEASES], [RELEASES]),
    }
    resources = {}
    job_arns = []
    for name, stage in STAGES.items():
        role = f"{name}Role"
        log_prefix = f"/is459/aml/fresh-bq2/${{DeploymentId}}/{stage}"
        reads, writes = access[stage]
        resources[role] = glue_role(stage, reads, writes, log_prefix)
        job_name = f"{NAMESPACE}-{stage}"
        job_arns.append(sub(f"arn:aws:glue:{REGION}:{ACCOUNT}:job/{job_name}"))
        resources[f"{name}Job"] = {
            "Type": "AWS::Glue::Job",
            "Properties": {
                "Name": sub(job_name),
                "Role": attr(role, "Arn"),
                "Command": {"Name": "glueetl", "PythonVersion": "3", "ScriptLocation": sub(s3 + CODE + "fresh_glue.py")},
                "GlueVersion": "5.1",
                "WorkerType": "G.1X",
                "NumberOfWorkers": WORKERS,
                "Timeout": TIMEOUT_MINUTES,
                "MaxRetries": 0,
                "ExecutionClass": "STANDARD",
                "ExecutionProperty": {"MaxConcurrentRuns": 1},
                "JobRunQueuingEnabled": False,
                "NonOverridableArguments": {
                    "--stage": stage,
                    "--bucket": BUCKET,
                    "--bucket-owner": ACCOUNT,
                    "--model-bundle-uri": sub(s3 + MODELS),
                    "--model-bundle-sha256": ref("ModelBundleSha256"),
                    "--job-language": "python",
                    "--job-bookmark-option": "job-bookmark-disable",
                    "--custom-logGroup-prefix": sub(log_prefix),
                    "--TempDir": sub(s3 + f"fresh-bq2/temp/${{DeploymentId}}/{stage}/"),
                    "--enable-spark-ui": "false",
                    "--enable-metrics": "false",
                    "--enable-observability-metrics": "false",
                    "--enable-job-insights": "false",
                    "--extra-py-files": sub(s3 + CODE + "fresh-bq2.zip"),
                    "--additional-python-modules": sub(s3 + CODE + "runtime.gluewheels.zip"),
                    "--python-modules-installer-option": "--no-index",
                },
                "Tags": {"Project": "is459-aml", "Phase": "fresh-bq2-smoke"},
            },
        }

    def invoker(service: str, source_arn: str, actions: str | list[str], targets: str | dict | list) -> dict:
        policy = trust(service)
        policy["Statement"][0]["Condition"] = {
            "StringEquals": {"aws:SourceAccount": ACCOUNT},
            "ArnEquals": {"aws:SourceArn": sub(source_arn)},
        }
        return {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "AssumeRolePolicyDocument": policy,
                "Policies": [{
                    "PolicyName": "InvokeFreshBQ2",
                    "PolicyDocument": {"Version": "2012-10-17", "Statement": [allow(actions, targets)]},
                }],
            },
        }

    resources["WorkflowRole"] = invoker(
        "states.amazonaws.com", state_machine_arn,
        ["glue:StartJobRun", "glue:GetJobRun", "glue:GetJobRuns", "glue:BatchStopJobRun"], job_arns,
    )
    resources["Workflow"] = {
        "Type": "AWS::StepFunctions::StateMachine",
        "Properties": {
            "StateMachineName": sub(NAMESPACE),
            "StateMachineType": "STANDARD",
            "RoleArn": attr("WorkflowRole", "Arn"),
            "DefinitionString": json.dumps(workflow_definition()),
            "DefinitionSubstitutions": {f"{name}Job": ref(f"{name}Job") for name in STAGES},
        },
    }
    resources["ReadyEventRole"] = invoker("events.amazonaws.com", trigger_arn,
                                          "states:StartExecution", sub(state_machine_arn))
    resources["ReadyEvent"] = {
        "Type": "AWS::Events::Rule",
        "Properties": {
            "Name": sub(NAMESPACE + "-ready"),
            "State": "DISABLED",
            "EventPattern": {
                "source": ["aws.s3"],
                "detail-type": ["Object Created"],
                "account": [ACCOUNT],
                "region": [REGION],
                "detail": {"bucket": {"name": [BUCKET]}, "object": {"key": [{"wildcard": READY}]}},
            },
            "Targets": [{
                "Id": "FreshBQ2",
                "Arn": ref("Workflow"),
                "RoleArn": attr("ReadyEventRole", "Arn"),
                "RetryPolicy": {"MaximumRetryAttempts": 0},
                "InputTransformer": {
                    "InputPathsMap": {"key": "$.detail.object.key", "etag": "$.detail.object.etag",
                                      "attempt": "$.id"},
                    "InputTemplate": '{"ready_key": <key>, "ready_etag": <etag>, "attempt_id": <attempt>}',
                },
            }],
        },
    }
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Isolated fresh BQ2 smoke in us-east-1 with five bounded Glue jobs and a disabled upload rule.",
        "Parameters": {
            "DeploymentId": {"Type": "String", "AllowedPattern": "[a-z0-9][a-z0-9-]{0,19}"},
            "CodeVersion": {"Type": "String", "AllowedPattern": "[a-f0-9]{64}"},
            "ModelBundleId": {"Type": "String", "AllowedPattern": "[A-Za-z0-9][A-Za-z0-9_-]{0,63}"},
            "ModelBundleSha256": {"Type": "String", "AllowedPattern": "[a-f0-9]{64}"},
        },
        "Resources": resources,
        "Outputs": {"WorkflowArn": {"Value": ref("Workflow")}},
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
