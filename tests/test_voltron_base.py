import datetime
import unittest
import json
from unittest import mock
from src.voltronsecurity.voltron_base import VoltronEncoder, VoltronFinding


class TestVoltronEncoder(unittest.TestCase):
    def test_encoder(self):
        payload = mock.Mock()
        payload.findingOutput.return_value = {}
        results = json.dumps(payload, cls=VoltronEncoder)
        payload.findingOutput.assert_called()


class TestVoltronBaseFinding(unittest.TestCase):
    def setUp(self):
        # create a sample payload dictionary to use for testing
        self.base_payload = {
            "toolName": "Voltron",
            "resourceType": "robot",
            "resourceId": "abcdedf",
            "toolFindingId": "myfindingid",
            "toolFindingSummary": "my summary text",
            "toolFindingJson": {"a": 1, "b": "abc"},
            "toolFindingURL": "https://example.site/abc",
            "toolFindingSeverity": "High",
            "voltronSeverity": "High",
            "extractDate": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    # @mock.patch(VoltronFinding.processPayload())
    def test_init(self):
        # create an instance of the VoltronFinding class using the sample payload
        finding = VoltronFinding(self.base_payload)

        # check that the payload was properly assigned to the __dict__ attribute
        self.assertEqual(finding.__dict__, self.base_payload)

    def test_repr(self):
        # create an instance of the VoltronFinding class using the sample payload
        finding = VoltronFinding(self.base_payload)

        # check that the __repr__ method returns a properly formatted JSON string
        self.assertEqual(finding.__repr__(), json.dumps(self.base_payload, indent=1))

    def test_finding_output(self):
        finding = VoltronFinding(self.base_payload)
        result = finding.findingOutput()
        required_fields = [
            "toolName",
            "resourceType",
            "resourceId",
            "toolFindingId",
            "toolFindingSummary",
            "toolFindingJson",
            "toolFindingURL",
            "toolFindingSeverity",
            "voltronSeverity",
            "extractDate",
            "findingDate",
        ]
        missing_fields = []
        for field in required_fields:
            if result.get(field) is None:
                missing_fields.append(field)
        self.assertEqual(
            len(missing_fields), 0, "Missing fields: {}".format(missing_fields)
        )
