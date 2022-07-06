from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as alb
from aws_cdk import aws_elasticloadbalancingv2_targets as target
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam 
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
            machine_image=ec2.MachineImage.latest_amazon_linux(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
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
        # ! ALB target group definition
        self.tg_1 = alb.ApplicationTargetGroup(self,
            id='sm-snowbit-tg-1',
            target_type=alb.TargetType.INSTANCE,
            port=80,
            vpc=self.vpc,
            targets=[instance_target_1]
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
        self.transactional_data = dynamodb.Table(self, "TransactionalDataTable",
        partition_key=dynamodb.Attribute(name="aws_account_id", type=dynamodb.AttributeType.STRING),
        # replication_regions=["us-east-1", "us-east-2"],
        billing_mode=dynamodb.BillingMode.PROVISIONED
        )

        self.transactional_data.auto_scale_write_capacity(
            min_capacity=1,
            max_capacity=10
        ).scale_on_utilization(target_utilization_percent=75)
        
        # ! Reference Data DynamoDB Table
        self.reference_data = dynamodb.Table(self, "ReferenceDataTable",
        partition_key=dynamodb.Attribute(name="aws_account_id", type=dynamodb.AttributeType.STRING),
        # replication_regions=["us-east-1", "us-east-2"],
        billing_mode=dynamodb.BillingMode.PROVISIONED
        )

        self.reference_data.auto_scale_write_capacity(
            min_capacity=1,
            max_capacity=10
        ).scale_on_utilization(target_utilization_percent=75)

        # ! PUBLIC EC2 TO REFERENCE TABLE
        self.ec2_instance_2.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=['dynamodb:Getitem'],
                resources=[self.reference_data.table_arn]
            )
        )

        # ! PRIVATE EC2 TO TRANSACTIONAL TABLE 
        self.ec2_instance_3.add_to_role_policy(
            statement=aws_iam.PolicyStatement(
                actions=['dynamodb:Getitem', 'dynamodb:PutItem', 'dynamodb:UpdateItem'],
                resources=[self.transactional_data.table_arn]
            )
        )
