from aws_cdk import (
    aws_events as events,
    aws_lambda as lambda_,
    aws_events_targets as targets,
    aws_iam as iam_,
    aws_logs as logs_,
    aws_sns as sns_,
    aws_cloudwatch as cloudwatch_,
    aws_cloudwatch_actions as cloudwatch_actions,
    core,
)
from aws_cdk.core import Duration


class AvailabilityCanaryStack(core.Stack):
    def __init__(self, app: core.App, id: str) -> None:
        super().__init__(app, id)

        lambda_fn = lambda_.Function(self, "AvailabilityCanary",
                                     runtime=lambda_.Runtime.PYTHON_3_8,
                                     code=lambda_.Code.from_asset("lambda_function.zip"),
                                     handler="availability-canary.lambda_handler",
                                     environment=dict(SSM_PATH='/epic-shelter'),
                                     function_name='availability-canary',
                                     memory_size=128,
                                     timeout=core.Duration.seconds(10),
                                     log_retention=logs_.RetentionDays.ONE_WEEK
                                     )

        ssm_get_by_path_policy = iam_.PolicyStatement(
            actions=["ssm:GetParametersByPath"],
            effect=iam_.Effect.ALLOW,
            sid="SSMGetParamsByPath",
            resources=['arn:aws:ssm:us-east-1:476889715112:parameter/epic-shelter']
        )
        lambda_fn.add_to_role_policy(ssm_get_by_path_policy)

        rule = events.Rule(self, "AvailabilityCanaryEventRule",
                           schedule=events.Schedule.rate(Duration.minutes(1))
                           )
        rule.add_target(targets.LambdaFunction(lambda_fn))

        sns_alert = sns_.Topic(self, "AvailabilityCanarySNSAlert", ).from_topic_arn(
            self,
            id="AvailabilityCanarySNSTopic",
            topic_arn="arn:aws:sns:us-east-1:476889715112:unhealthyHost"
        )
        alarm_action = cloudwatch_actions.SnsAction(topic=sns_alert)

        errors_alarm = cloudwatch_.Metric(
            namespace="AWS/Lambda",
            metric_name="Errors",
        ).create_alarm(self, "AvailabilityCanaryErrorsAlarm",
                       evaluation_periods=5,
                       threshold=1,
                       period=core.Duration.seconds(60),
                       treat_missing_data=cloudwatch_.TreatMissingData.BREACHING,
                       statistic="Sum",
                       alarm_name="AvailabilityCanaryErrorsAlarm",
                       comparison_operator=cloudwatch_.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
                       )

        invocations_alarm = cloudwatch_.Metric(
            namespace="AWS/Lambda",
            metric_name="Invocations",
        ).create_alarm(self, "AvailabilityCanaryInvocationsAlarm",
                       evaluation_periods=5,
                       threshold=1,
                       period=core.Duration.seconds(60),
                       treat_missing_data=cloudwatch_.TreatMissingData.BREACHING,
                       statistic="Sum",
                       alarm_name="AvailabilityCanaryInvocationsAlarm",
                       comparison_operator=cloudwatch_.ComparisonOperator.LESS_THAN_THRESHOLD
                       )

        errors_alarm.add_alarm_action(alarm_action)
        invocations_alarm.add_alarm_action(alarm_action)


app = core.App()
AvailabilityCanaryStack(app, "AvailabilityCanaryStack")
app.synth()
