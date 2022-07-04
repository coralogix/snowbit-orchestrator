import enum


class Severity(enum.Enum):
    LOW = 0
    MID = 1
    HIGH = 2
    CRITICAL = 3


class Validate:
    def __init__(self, process_json):
        self.p_data = process_json

    def localize(self):
        flag = 0
        try:
            if isinstance(self.p_data['accountId'], int) and len(self.p_data['accountId']) == 12:
                if isinstance(self.p_data['alertDescription'], str) and len(self.p_data['alertDescription']) >= 31:
                    if isinstance(self.p_data['alertName'], str) and len(self.p_data['alertName']) == 120:
                        if isinstance(self.p_data['alertSeverity'], enum.EnumMeta) and (self.p_data['alertSeverity']) in type(self.p_data['alertSeverity'].__name__):
                            flag = 1
        except KeyError:
            # should this error be logged using boto3 to cloudwatch ?
            pass

        if flag == 1:
            return "VALID"
        else:
            return "INVALID"









