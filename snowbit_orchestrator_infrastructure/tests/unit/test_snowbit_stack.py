import aws_cdk as core
import aws_cdk.assertions as assertions

from snowbit.snowbit_stack import SnowbitStack

# example tests. To run these tests, uncomment this file along with the example
# resource in snowbit/snowbit_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = SnowbitStack(app, "snowbit")
    template = assertions.Template.from_stack(stack)


    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Handler": "dbstream_function.handler",
            "Runtimne": "Python3.7"
        },
    )

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
