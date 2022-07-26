from aws_cdk import RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as alb
from aws_cdk import aws_elasticloadbalancingv2_targets as target
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam 
from aws_cdk import aws_lambda
from aws_cdk import aws_sqs
from aws_cdk import aws_lambda_event_sources
from aws_cdk import aws_logs
from aws_cdk import aws_s3
from aws_cdk import aws_ssm
from aws_cdk import aws_autoscaling
from constructs import Construct

class SnowbitStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # ! VPC and Subnets
        self.vpc = ec2.Vpc(self, 
            id="sm-snowbit-vpc",
            max_azs=3,
            cidr='10.0.0.0/16',
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="sm-snowbit-subnet-public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="sm-snowbit-subnet-private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT,
                    cidr_mask=24
                )
            ])

        # ! Public subnet security group
        self.sg = ec2.SecurityGroup(self, 
            id='sm-snowbit-sg',
            vpc=self.vpc,
            allow_all_outbound=True
        )
        self.sg.add_ingress_rule(peer=ec2.Peer.any_ipv4(), connection=ec2.Port.tcp(22), description='Allow SSH from anywhere')
        self.sg.add_ingress_rule(peer=ec2.Peer.any_ipv4(), connection=ec2.Port.tcp(80), description='Allow HTTP from anywhere')

        # ! ALB security group
        self.sg_alb = ec2.SecurityGroup(self,
            id='sm-snowbit-alb-sg',
            vpc=self.vpc,
            allow_all_outbound=False
        )
        self.sg_alb.add_egress_rule(peer=ec2.Peer.security_group_id(self.sg.security_group_id), connection=ec2.Port.tcp(80), description='Allow health check')
        self.sg_alb.add_ingress_rule(peer=ec2.Peer.any_ipv4(), connection=ec2.Port.all_tcp(), description="Allow all inbound traffic")

        self.sg_private = ec2.SecurityGroup(self,
            id='sm-snowbit-private-sg',
            vpc=self.vpc,
            allow_all_outbound=True
        )
        self.sg_private.add_ingress_rule(peer=ec2.Peer.security_group_id(self.sg.security_group_id), connection=ec2.Port.tcp(22), description='Allow SSH from public subnet')
        self.sg_private.add_ingress_rule(peer=ec2.Peer.security_group_id(self.sg.security_group_id), connection=ec2.Port.tcp(80), description='Allow HTTP from public subnet')

        # ! Public instance - 1
        self.ec2_instance = ec2.Instance(self,
            id='sm-snowbit-instance',
            vpc=self.vpc,
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE2, ec2.InstanceSize.NANO),
            machine_image=ec2.MachineImage.generic_linux(
                {'us-east-1': 'ami-083654bd07b5da81d'}
            ),
            key_name="demokeyyt18",
            security_group=self.sg,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            )
        )

        with open('./lib/post_initialization.sh', 'r', encoding='utf-8') as file:
            user_data = file.read()

        self.ec2_instance.add_user_data(user_data)
        
        # ! Public instance - 2
        self.ec2_instance_2 = ec2.Instance(self,
            id='sm-snowbit-instance-2',
            vpc=self.vpc,
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE2, ec2.InstanceSize.NANO),
            machine_image=ec2.MachineImage.generic_linux(
                {'us-east-1': 'ami-083654bd07b5da81d'}
            ),
            key_name="demokeyyt18",
            security_group=self.sg,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            )
        )

        # ! Private instance 
        self.ec2_instance_3 = ec2.Instance(self,
            id='sm-snowbit-instance-3',
            vpc=self.vpc,
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE2, ec2.InstanceSize.NANO),
            machine_image=ec2.MachineImage.generic_linux(
                {'us-east-1': 'ami-083654bd07b5da81d'}
            ),
            key_name="demokeyyt18",
            security_group=self.sg,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT
            )
        )
        
        # ! Target instances
        instance_target_1 = target.InstanceTarget(self.ec2_instance_2, port=80)
        instance_target_2 = target.InstanceTarget(self.ec2_instance, port=80)
        # ! ALB target group definition
        self.tg_1 = alb.ApplicationTargetGroup(self,
            id='sm-snowbit-tg-1',
            target_type=alb.TargetType.INSTANCE,
            port=80,
            vpc=self.vpc,
            targets=[instance_target_1, instance_target_2]
        )
        
        # ! Application Load Balancer
        self.alb = alb.ApplicationLoadBalancer(self, 
            id='sm-snowbit-alb',
            internet_facing=True,
            vpc=self.vpc,
            security_group=self.sg_alb
        )
        # ! ALB Listener
        self.listener = self.alb.add_listener(
            id='sm-snowbit-listener',
            port=80
        )
        # ! ALB Target group
        self.listener.add_target_groups(
            id='sm-snowbit-target-group',
            target_groups=[self.tg_1]
        )
        # ! Transaction Data DynamoDB Table
        self.transactional_data = dynamodb.Table(self, "tbl_Transactional_Data_Table",
        partition_key=dynamodb.Attribute(name="timestamp", type=dynamodb.AttributeType.STRING),
        # replication_regions=["us-east-1", "us-east-2"],
        billing_mode=dynamodb.BillingMode.PROVISIONED,
        removal_policy=RemovalPolicy.DESTROY,
        stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        time_to_live_attribute='ttl'
        )

        self.transactional_data.auto_scale_write_capacity(
            min_capacity=1,
            max_capacity=10
        ).scale_on_utilization(target_utilization_percent=75)
        
        # ! Reference Data DynamoDB Table
        self.reference_data = dynamodb.Table(self, "tbl_Reference_Data_Table",
        partition_key=dynamodb.Attribute(name="account_id", type=dynamodb.AttributeType.STRING),
        # replication_regions=["us-east-1", "us-east-2"],
        billing_mode=dynamodb.BillingMode.PROVISIONED,
        removal_policy=RemovalPolicy.DESTROY
        )

        self.reference_data.auto_scale_write_capacity(
            min_capacity=1,
            max_capacity=10
        ).scale_on_utilization(target_utilization_percent=75)

        # ! Webhook Data DynamoDB Table
        self.webhook_data = dynamodb.Table(self, "tbl_Webhook_Data_Table",
        partition_key=dynamodb.Attribute(name="alert_id", type=dynamodb.AttributeType.STRING),
        billing_mode=dynamodb.BillingMode.PROVISIONED,
        removal_policy=RemovalPolicy.DESTROY
        )

        self.webhook_data.auto_scale_write_capacity(
            min_capacity=1,
            max_capacity=10
        ).scale_on_utilization(target_utilization_percent=75)

        self.transactional_data.apply_removal_policy(RemovalPolicy.DESTROY)
        self.reference_data.apply_removal_policy(RemovalPolicy.DESTROY)
        self.webhook_data.apply_removal_policy(RemovalPolicy.DESTROY)

        # ! Lambda Role for LambdaDBExecution
        self.lambda_role = aws_iam.Role(self, "LambdaRole",
        assumed_by=aws_iam.ServicePrincipal("lambda.amazonaws.com"),
        description="DynamoDB executionRole for Lambda"
        )

        self.lambda_role.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaDynamoDBExecutionRole"))

        # ! Policy to grant lambda access to aws-secrets
        self.lambda_role.attach_inline_policy(
            aws_iam.Policy(self, 'secret-policy',
            statements=[
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions = [
                        "secretsmanager:GetRandomPassword", 
                        "secretsmanager:GetResourcePolicy", 
                        "secretsmanager:GetSecretValue", 
                        "secretsmanager:DescribeSecret", 
                        "secretsmanager:ListSecretVersionIds"

                    ],
                    resources= ['*']
                )
            ])
        )

        # ! Zenpy distribution for lambda as lambda layer
        self.zenpy_lambdaLayer = aws_lambda.LayerVersion(self, 'zenpy-lambda-layer',
                  code = aws_lambda.AssetCode('layer/'),
                  compatible_runtimes = [aws_lambda.Runtime.PYTHON_3_7],
        ) 

        # ! Lambda for DB streams
        self.lambda_dbstream = aws_lambda.Function(
            self, 'LambdaDBstreamshandler',
            runtime= aws_lambda.Runtime.PYTHON_3_7,
            code= aws_lambda.Code.from_asset('lambda'),
            layers=[self.zenpy_lambdaLayer],
            handler='dbstream_function.handler',
            role=self.lambda_role,
        )

        self.stream_queue = aws_sqs.Queue(self, "streamqueue")
        self.lambda_dbstream.add_event_source(aws_lambda_event_sources.DynamoEventSource(self.transactional_data,
        starting_position=aws_lambda.StartingPosition.TRIM_HORIZON,
        batch_size=5,
        bisect_batch_on_error=True,
        on_failure=aws_lambda_event_sources.SqsDlq(self.stream_queue),
        retry_attempts=10
        ))

        # ! Custom Log groups
        self.so_log_group = aws_logs.LogGroup(self, "SO Log Group")
        self.so_log_bucket = aws_s3.Bucket(self, "SO Log S3 Bucket")

        self.so_log_group.add_to_resource_policy(aws_iam.PolicyStatement(
        actions=["logs:CreateLogStream", "logs:PutLogEvents"],
        principals=[aws_iam.ServicePrincipal("es.amazonaws.com")],
        resources=[self.so_log_group.log_group_arn]
        ))

        self.so_log_stream = aws_logs.LogStream(self, "SOLogStream",
        log_group=self.so_log_group,
        log_stream_name="SOlogStream",
        removal_policy=RemovalPolicy.DESTROY
        )

        # ! ssm parameters for ddb table names
        aws_ssm.StringParameter(self, "SsmStringParameterTransactionalTable",
        allowed_pattern=".*",
        description="The name of the Transactional DynamoDB table",
        parameter_name="transactional_db_name",
        string_value=self.transactional_data.table_name,
        tier=aws_ssm.ParameterTier.ADVANCED,
        )

        aws_ssm.StringParameter(self, "SsmStringParameterReferenceTable",
        allowed_pattern=".*",
        description="The name of the Reference DynamoDB table",
        parameter_name="reference_db_name",
        string_value=self.reference_data.table_name,
        tier=aws_ssm.ParameterTier.ADVANCED,
        )

        aws_ssm.StringParameter(self, "SsmStringParameterWebhookTable",
        allowed_pattern=".*",
        description="The name of the Webhook data DynamoDB table",
        parameter_name="webhook_db_name",
        string_value=self.webhook_data.table_name,
        tier=aws_ssm.ParameterTier.ADVANCED,
        )

        instance_target_3 = target.InstanceTarget(self.ec2_instance_3, port=80)
        # ! INTERNAL APPLICATION LOAD BALANCER FOR SO 
        # self.ec2_instance_3
        self.internal_alb = alb.ApplicationLoadBalancer(self, 
            id='sm-snowbit-internal-alb',
            internet_facing=False,
            vpc=self.vpc,
            security_group=self.sg_private
        )
        self.tg_3 = alb.ApplicationTargetGroup(self,
            id='sm-snowbit-tg-3',
            target_type=alb.TargetType.INSTANCE,
            port=80,
            vpc=self.vpc,
            targets=[instance_target_3]
        )
         # ! ALB Listener
        self.private_listener = self.internal_alb.add_listener(
            id='sm-snowbit-private-listener',
            port=80
        )
        # ! ALB Target group
        self.private_listener.add_target_groups(
            id='sm-snowbit-target-group-3',
            target_groups=[self.tg_3]
        )

        # AUTOSCALING FOR EC2 INSTANCES
        aws_autoscaling.AutoScalingGroup(self, "SnowbitAutoScalingGroup",
        vpc=self.vpc,
        instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE2, ec2.InstanceSize.NANO),
        machine_image=ec2.AmazonLinuxImage(),
        security_group=self.sg,
        # desired_capacity=2
        )







        

        # # ! PUBLIC EC2 TO REFERENCE TABLE
        # self.ec2_instance_2.add_to_role_policy(
        #     aws_iam.PolicyStatement(
        #         actions=['dynamodb:Getitem'],
        #         resources=[self.reference_data.table_arn]
        #     )
        # )

        # # ! PRIVATE EC2 TO TRANSACTIONAL TABLE 
        # self.ec2_instance_3.add_to_role_policy(
        #     statement=aws_iam.PolicyStatement(
        #         actions=['dynamodb:Getitem', 'dynamodb:PutItem', 'dynamodb:UpdateItem'],
        #         resources=[self.transactional_data.table_arn]
        #     )
        # )
