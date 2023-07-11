import unittest
import datetime
import json
from unittest.mock import MagicMock, patch

from src.voltronsecurity.helpers import UNKNOWN_DATE
from src.voltronsecurity.voltron_snyk import (
    VoltronSnykCodeFinding,
    snykProject,
    snykOrg,
    snykFinding,
    SnykCodeCollector,
)


class TestVoltronSnykCodeFinding(unittest.TestCase):
    def test_processPayload(self):
        payload = {
            "repoName": "test_repo",
            "id": 123,
            "longTitle": "Test finding",
            "issueLink": "https://example.com/issue",
            "severity": "high",
        }
        finding = VoltronSnykCodeFinding(payload)

        self.assertEqual(finding.toolName, "SnykCode")
        self.assertEqual(finding.resourceType, "CodeRepo")
        self.assertEqual(finding.resourceId, "test_repo")
        self.assertEqual(finding.toolFindingId, 123)
        self.assertEqual(finding.toolFindingSummary, "Test finding")
        self.assertEqual(finding.toolFindingURL, "https://example.com/issue")
        self.assertEqual(finding.toolFindingSeverity, "high")
        self.assertEqual(finding.voltronSeverity, "high")
        self.assertIsNotNone(finding.extractDate)
        self.assertEqual(finding.findingDate, UNKNOWN_DATE)


class TestSnykFinding(unittest.TestCase):
    def setUp(self):
        self.response_data = {
            "attributes": {
                "title": "Test finding",
                "primaryFilePath": "path/to/file",
                "primaryRegion": "region",
            }
        }
        self.snykData = {
            "id": 123,
            "attributes": {},
            "links": {"self": "https://example.com/finding"},
        }

    def test_repr(self):
        finding = snykFinding(self.snykData)
        expected = json.dumps(finding.__dict__, indent=1)
        self.assertEqual(expected, finding.__repr__())

    def test_decorate_issue(self):
        apiHandler = MagicMock()
        apiHandler.get_finding_data.return_value = self.response_data

        projectObject = MagicMock()
        projectObject.orgData = {"slug": "test_org"}
        finding = snykFinding(self.snykData, projectObject)

        finding.decorate_issue(apiHandler)

        self.assertEqual(finding.longTitle, "Test finding")
        self.assertEqual(finding.primaryFilePath, "path/to/file")
        self.assertEqual(finding.locationData, "region")


class TestSnykOrg(unittest.TestCase):
    def test_init(self):
        orgData = {"name": "test_org", "url": "https://example.com/org", "id": 123}
        org = snykOrg(orgData)

        self.assertEqual(org.orgName, "test_org")
        self.assertEqual(org.orgURL, "https://example.com/org")
        self.assertEqual(org.orgId, 123)

        expected = json.dumps(org.__dict__, indent=1)
        self.assertEqual(expected, org.__repr__())


class TestSnykProject(unittest.TestCase):
    def setUp(self):
        self.project_data = {
            "id": 123,
            "attributes": {},
            "relationships": {
                "target": {"links": {"related": "https://example.com/project"}}
            },
        }
        self.org_data = {
            "name": "test_org",
            "url": "https://example.com/org",
            "id": 456,
        }

    def test_init(self):
        project = snykProject(self.project_data, self.org_data)
        expected = json.dumps(project.__dict__, indent=1)
        self.assertEqual(expected, project.__repr__())
        self.assertEqual(project.id, 123)
        self.assertEqual(project.urlPath, "https://example.com/project")
        self.assertEqual(project.orgData, self.org_data)

    def test_project_exception(self):
        with self.assertRaises(KeyError):
            project = snykProject({}, self.org_data)


class TestSnykCodeCollector(unittest.TestCase):
    def setUp(self) -> None:
        self.test_key = "abc123"
        self.test_org_data = {
            "name": "test_org",
            "url": "https://example.com/org",
            "id": 456,
        }

    @patch("src.voltronsecurity.voltron_snyk.SnykCodeCollector.gen_session")
    @patch("src.voltronsecurity.voltron_snyk.SnykCodeCollector.get_orgs")
    @patch("src.voltronsecurity.voltron_snyk.SnykCodeCollector.gen_org_data")
    def test_scc_init(self, mock_gen_org, mock_get_orgs, mock_gen_Session):
        handler = SnykCodeCollector(self.test_key)
        self.assertEqual(self.test_key, handler.api_key)

    def test_scc_gen_session(self):
        handler = SnykCodeCollector(self.test_key, [], {})
        self.assertEqual("application/json", handler.session.headers["Content-Type"])
        self.assertEqual(
            "token {}".format(self.test_key), handler.session.headers["Authorization"]
        )

    # def test_scc_gen_project_data(self):
    #    handler = SnykCodeCollector(self.test_key, [], self.test_org_data)

    def test_scc_gen_issue_data(self):
        pass

    def test_scc_paginated_get_request(self):
        pass

    def test_scc_get_orgs(self):
        pass

    def test_scc_get_projects(self):
        pass

    def test_scc_get_all_code_issues(self):
        pass

    def test_scc_get_finding_data(self):
        pass

    def test_scc_write_csv(self):
        pass

    def test_scc_write_object_csv(self):
        pass

    def test_write_to_table(self):
        pass
