import csv
import requests
import json
import logging
import os
from datetime import datetime
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

from voltronsecurity import helpers
from voltronsecurity.voltron_base import VoltronFinding

FORMAT = "[%(filename)s:%(lineno)s - %(funcName)s() ] %(message)s"
logging.basicConfig(format=FORMAT)
logger = logging.getLogger("wiz")
logger.setLevel(os.environ.get("APP_LOGLEVEL", logging.DEBUG))


class VoltronWizFinding(VoltronFinding):
    def processPayload(self, payload):
        results = {
            "toolName": "Wiz",
            "resourceType": payload["entitySnapshot"]["type"],
            "resourceId": payload["entitySnapshot"]["externalId"],
            "toolFindingId": payload["id"],
            "toolFindingSummary": payload["control"]["name"],
            "toolFindingJson": json.dumps(payload),
            "toolFindingURL": "https://app.wiz.io/issues#~(issue~'{})".format(
                payload["id"]
            ),
            "toolFindingSeverity": payload["severity"],
            "voltronSeverity": payload["severity"],
            "extractDate": helpers.get_time(),
            "findingDate": datetime.strptime(
                payload["createdAt"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ).isoformat(),
        }
        return results


class WizBaseApi:
    def __init__(
        self,
        wiz_url="https://api.us2.app.wiz.io",
        wiz_auth_url="https://auth.app.wiz.io",
    ):
        self.base_url = wiz_url
        self.auth_url = wiz_auth_url

    def gen_client(self, client_id, client_secret, headers=None):
        if headers is None:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            }
        session = requests.Session()
        session.headers.update(headers)
        # Get an auth token, then update the session
        token = self.get_token(session, client_id, client_secret)
        auth = f"Bearer {token}"

        url = self.base_url + "/graphql"
        transport = RequestsHTTPTransport(
            url=url, verify=True, retries=5, headers={"Authorization": auth}
        )
        client = Client(transport=transport, fetch_schema_from_transport=False)
        return client, session

    def get_token(self, session, client_id, client_secret):
        auth_url = f"{self.auth_url}/oauth/token"
        payload = f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}&audience=wiz-api"
        resp = session.post(auth_url, payload)
        token = resp.json()["access_token"]
        return token

    def _query_paginator(self, gql_client, query_name, query, variables):
        result = gql_client.execute(query, variable_values=variables)
        yield result
        while result[query_name]["pageInfo"]["hasNextPage"]:
            variables["after"] = result[query_name]["pageInfo"]["endCursor"]
            try:
                result = gql_client.execute(query, variable_values=variables)
                yield result
            except Exception as e:
                if "502: Bad Gateway" not in str(
                    e
                ) and "503: Service Unavailable" not in str(e):
                    print("<p>WizIngestion-Error: %s</p>" % str(e))
                    break
                else:
                    logger.warning(
                        "Error: {errorstr}\n Retrying...".format(errorstr=str(e))
                    )
                    continue

    def run_query(self, gql_client, query, qname, qvars):
        results = []

        for resp in self._query_paginator(gql_client, qname, query, qvars):
            try:
                results.extend(resp[qname]["nodes"])
            except KeyError:
                logger.info("No nodes")
                continue
        return results


class WizCollector:
    def __init__(self, client_id, client_secret):
        self.wiz_api = WizBaseApi()
        self.api_client, self.session = self.wiz_api.gen_client(
            client_id, client_secret
        )

    def get_projects(self):
        query_name = "projects"
        query_vars = {
            "first": 100,
            "filterBy": {},
        }
        query = gql(
            "query ProjectsTable($filterBy: ProjectFilters, $first: Int, $after: String, $orderBy: ProjectOrder,) { projects(filterBy: $filterBy, first: $first, after: $after, orderBy: $orderBy) { nodes { id name slug archived } pageInfo { hasNextPage endCursor } totalCount LBICount MBICount HBICount }}"
        )
        result = self.wiz_api.run_query(self.api_client, query, query_name, query_vars)
        logger.debug({"projects": result})
        return result

    def get_all_issues(self, project_id):
        query_name = "issues"
        query_vars = {
            "first": 500,
            "filterBy": {
                "project": [project_id],
                "status": ["OPEN", "IN_PROGRESS"],
                "relatedEntity": {},
            },
            "orderBy": {"field": "SEVERITY", "direction": "DESC"},
        }

        query = gql(
            "query IssuesTable($filterBy: IssueFilters, $first: Int, $after: String, $orderBy: IssueOrder) { issues(filterBy: $filterBy, first: $first, after: $after, orderBy: $orderBy) { nodes {  ...IssueDetails } pageInfo {  hasNextPage  endCursor } totalCount } }  fragment IssueDetails on Issue { id control { id name securitySubCategories {  id  category {  id  } } } createdAt updatedAt status severity entity { id name type } resolutionReason entitySnapshot { id type name cloudPlatform cloudProviderURL region subscriptionName externalId subscriptionId subscriptionExternalId subscriptionTags nativeType } notes { id text } }"
        )
        result = self.wiz_api.run_query(self.api_client, query, query_name, query_vars)
        return result
