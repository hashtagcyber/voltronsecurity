import datetime
import json
import logging
import typing

FORMAT = "[%(filename)s:%(lineno)s - %(funcName)s() ] %(message)s"
logging.basicConfig(format=FORMAT)
logger = logging.getLogger("voltron")

UNKNOWN_DATE = datetime.datetime.strptime(
    "20/04/1969 14:20:00", "%d/%m/%Y %H:%M:%S"
).isoformat()


class VoltronEncoder(json.JSONEncoder):
    """This class allows you to json.dumps() any VoltronFinding:
    json.dumps(finding, cls=VoltronEncoder)
    """

    def default(self, finding):
        return finding.findingOutput()


class VoltronFindingOutput(typing.TypedDict):
    toolName: str
    resourceType: str
    resourceId: str
    toolFindingId: str
    toolFindingSummary: str
    toolFindingJson: str
    toolFindingURL: str
    toolFindingSeverity: str
    voltronSeverity: str
    extractDate: str
    findingDate: str


class VoltronFinding:
    def __init__(self, payload: dict):
        attribs = self.processPayload(payload)
        self.__dict__.update(attribs)

    def __repr__(self):
        return json.dumps(self.__dict__, indent=1)

    def processPayload(self, payload: dict) -> dict:
        """Override this method in child classes"""
        payload["findingDate"] = "0"
        return payload

    def findingOutput(self) -> VoltronFindingOutput:
        """Return a Dict containing all Voltron Standard Fields"""
        return {
            "toolName": self.toolName,
            "resourceType": self.resourceType,
            "resourceId": self.resourceId,
            "toolFindingId": self.toolFindingId,
            "toolFindingSummary": self.toolFindingSummary,
            "toolFindingJson": json.dumps(self.toolFindingJson),
            "toolFindingURL": self.toolFindingURL,
            "toolFindingSeverity": self.toolFindingSeverity,
            "voltronSeverity": self.voltronSeverity,
            "extractDate": self.extractDate,
            "findingDate": self.findingDate,
        }
