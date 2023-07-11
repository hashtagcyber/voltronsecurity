import csv
import requests
import json
import logging
import os
import datetime

from voltronsecurity.helpers import UNKNOWN_DATE
from voltronsecurity.voltron_base import VoltronFinding

FORMAT = "[%(filename)s:%(lineno)s - %(funcName)s() ] %(message)s"
logging.basicConfig(format=FORMAT)
logger = logging.getLogger("snykcode")


class VoltronSnykCodeFinding(VoltronFinding):
    def __init__(self, payload):
        """Abstract the SnykCode finding into something that can compare with other tools"""
        self.processPayload(payload)

    def processPayload(self, payload):
        self.toolName = "SnykCode"
        self.resourceType = "CodeRepo"
        self.resourceId = payload["repoName"]
        self.toolFindingId = payload["id"]
        self.toolFindingSummary = payload["longTitle"]
        self.toolFindingJson = payload
        self.toolFindingURL = payload["issueLink"]
        self.toolFindingSeverity = payload["severity"]
        self.voltronSeverity = payload["severity"]
        self.extractDate = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.findingDate = UNKNOWN_DATE


class snykFinding:
    def __init__(self, snykData, projectObject=None):
        self.__dict__ = snykData["attributes"]
        self.id = snykData["id"]
        self.issueURL = snykData["links"]["self"]
        self.projectId = None
        self.primaryFilePath = None
        self.issueLink = None
        # self.foundDate = None
        self.orgName = None
        self.repoName = None
        # self.deepLink = None
        # self.committedBy = None
        if projectObject is not None:
            self.orgName = projectObject.orgData["slug"]
            self.repoName = projectObject.name
            self.projectId = projectObject.id
            self.issueLink = "https://app.snyk.io/org/{}/project/{}#issue-{}".format(
                self.orgName, self.projectId, self.id
            )

    def decorate_issue(self, apiHandler):
        response_data = apiHandler.get_finding_data(self.issueURL)
        self.longTitle = response_data["attributes"]["title"]
        self.primaryFilePath = response_data["attributes"]["primaryFilePath"]
        self.locationData = response_data["attributes"]["primaryRegion"]

    def __repr__(self):
        return json.dumps(self.__dict__, indent=1)


class snykOrg:
    def __init__(self, orgData):
        self.__dict__ = orgData
        self.orgName = orgData["name"]
        self.orgURL = orgData["url"]
        self.orgId = orgData["id"]

    def __repr__(self):
        return json.dumps(self.__dict__, indent=1)


class snykProject:
    def __init__(self, projectData, orgData):
        try:
            self.__dict__ = projectData["attributes"]
            self.id = projectData["id"]
            self.urlPath = projectData["relationships"]["target"]["links"]["related"]
            self.orgData = orgData
        except Exception as e:
            logger.error(projectData)
            raise e

    def __repr__(self):
        return json.dumps(self.__dict__, indent=1)


class SnykCodeCollector:
    def __init__(self, api_key, orgs=None, org_response_data=None):
        self.api_key = api_key
        self.session = self.gen_session(api_key)

        if org_response_data is None:
            org_response_data = self.get_orgs(self.session)
        self.orgData = self.gen_org_data(org_response_data)

        if orgs is None:
            orgs = [x["id"] for x in org_response_data]
        self.orgs = orgs

    def gen_session(self, api_key):
        logger.info("Started")
        session = requests.Session()
        headers = {
            "Content-Type": "application/json",
            "Authorization": "token " + api_key,
        }
        session.headers.update(headers)
        return session

    def gen_org_data(self, org_response):
        logger.info("Started")
        logger.info({"step": "genOrgDataStart"})
        orgData = {}
        for org in org_response:
            orgData[org["id"]] = snykOrg(org)
        return orgData

    def gen_project_data(self, project_response, org_id):
        logger.info("Started")
        projects = {}
        orgDict = self.orgData[org_id].__dict__
        for project in project_response:
            projects[project["id"]] = snykProject(project, orgDict)
        return projects

    def gen_issue_data(self, issue_response, project_object):
        logger.info("Started")
        issues = [snykFinding(entry, project_object) for entry in issue_response]
        for issue in issues:
            issue.decorate_issue(self)
        return issues

    def _paginated_get_request(
        self, session, target_endpoint, target_path, target_params
    ):
        logger.info("Started")
        target_url = "{}{}".format(target_endpoint, target_path)
        response = session.get(target_url, params=target_params)
        if response.status_code != 404:
            try:
                response.raise_for_status()
            except:
                logger.warning("Failed to get first page")
                return
        yield response

        next_url = response.json().get("links", {}).get("next")
        while next_url is not None:
            target_url = "{}{}".format(target_endpoint, next_url)
            response = session.get(target_url)
            next_url = response.json().get("links", {}).get("next")
            yield response

    def get_orgs(self, session=None):
        logger.info("Started")
        if session is None:
            session = self.session
        logger.info({"step": "getOrgsStart"})
        org_response = session.get("https://snyk.io/api/v1/orgs")
        if org_response.status_code == 200:
            orgData = org_response.json()["orgs"]
        else:
            logger.warning("Failed to get orgs.")
            orgData = []
        logger.info({"step": "getOrgsComplete", "resultCount": len(orgData)})
        return orgData

    def get_projects(self, org_id, session=None, as_dict=False):
        logger.info("Started")
        if session is None:
            session = self.session
        endpoint = "https://api.snyk.io/rest"
        urlpath = "/orgs/{}/projects".format(org_id)
        params = {"version": "beta", "limit": "100"}
        results = []
        for page in self._paginated_get_request(session, endpoint, urlpath, params):
            results.extend(page.json()["data"])
        if as_dict is True:
            results = self.gen_project_data(results, org_id)

        logger.info({"step": "getProjectsComplete", "resultCount": len(results)})
        return results

    def get_all_code_issues(
        self, orgObject, projectObject, session=None, as_dict=False
    ):
        logger.info("Started")
        if session is None:
            session = self.session
        endpoint = "https://api.snyk.io/rest"
        urlpath = "/orgs/{}/issues".format(orgObject.id)
        params = {
            "project_id": projectObject.id,
            "version": "2022-04-06~experimental",
            "limit": 100,
        }
        all_issues = []
        for page in self._paginated_get_request(session, endpoint, urlpath, params):
            try:
                all_issues.extend(page.json()["data"])
            except KeyError:
                logger.error("No data in response.")
                logger.error(page.json())
                continue

        if as_dict is True:
            logger.info("decorating {} issues".format(len(all_issues)))
            all_issues = self.gen_issue_data(all_issues, projectObject)

        return all_issues

    def get_finding_data(self, finding_path, session=None):
        logger.info("Started")
        if session is None:
            session = self.session

        endpoint = "https://api.snyk.io/rest"
        target_url = "{}{}".format(endpoint, finding_path)
        try:
            response = session.get(target_url)
            response.raise_for_status()
            results = response.json()["data"]
        except Exception as e:
            logger.error("Unable to get data for {}".format(target_url))
            logger.error(e)
            results = {
                "attributes": {
                    "title": "DecorationFailed",
                    "primaryFilePath": "DecorationFailed",
                    "primaryRegion": "DecorationFailed",
                }
            }
        return results

    def write_csv(self, results, outfile_name):
        logger.info("Started")
        path_string = os.path.dirname(outfile_name)
        date_string = datetime.now().strftime("%Y_%m_%d_")
        file_string = os.path.basename(outfile_name)
        outfile = path_string + "/" + date_string + file_string + ".csv"

        counter = 0
        with open(outfile, "w") as f:
            csv_writer = csv.writer(f)
            for finding in results:
                csv_writer.writerow(finding)
                counter += 1
        logger.info({"step": "writeCSVComplete", "resultCount": counter})
        return outfile

    def write_object_csv(self, results, outfile_name):
        logger.info("Started")
        dict_results = [x.__dict__ for x in results]
        header = dict_results[0].keys()
        with open(outfile_name, "w", encoding="utf8", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=header)
            writer.writeheader()
            writer.writerows(dict_results)


def write_to_table(pg_handler, tablename, inputlist):
    cursor = pg_handler.cursor()
    fillers = "%s," * len(inputlist[0])
    fillers = fillers.rstrip(",")
    statement = "INSERT INTO {} VALUES ({}) ON CONFLICT DO NOTHING".format(
        tablename, fillers
    )
    cursor.executemany(statement, inputlist)
    pg_handler.commit()
    cursor.close()
