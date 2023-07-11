import asyncio
import datetime
import hashlib
import json
import logging
import os
import requests

from typing import Optional

from voltronsecurity import helpers
from voltronsecurity.voltron_rabbitmq import VoltronRabbitMQQueue
from voltronsecurity.voltron_postgres import VoltronDB, VoltronPostgres
from voltronsecurity.voltron_base import (
    VoltronBaseProcessResponse,
    VoltronBaseQueryInterface,
    VoltronMessagePayload,
    VoltronFinding,
)

FORMAT = "[%(filename)s:%(lineno)s - %(funcName)s() ] %(message)s"
logging.basicConfig(format=FORMAT)
logger = logging.getLogger("rabbit-example")

SRC_QUEUE_HOST = os.getenv("SRC_QUEUE_HOST")
SRC_QUEUE_NAME = os.getenv("SRC_QUEUE_NAME")

DST_QUEUE_HOST = os.getenv("DST_QUEUE_HOST")
DST_QUEUE_NAME = os.getenv("DST_QUEUE_NAME")

DST_DB_HOST = os.getenv("DST_DB_HOST")
DST_DB_PORT = os.getenv("DST_DB_PORT", 5432)
DST_DB_USER = os.getenv("DST_DB_USER")
DST_DB_PASSWORD = os.getenv("DST_DB_PASSWORD")
DST_DB_NAME = os.getenv("DST_DB_NAME")
DST_DB_TABLE = os.getenv("DST_DB_TABLE")

sample_messages = [
    {
        "handlerName": "TotallyLegitSiteQueryHandler",
        "handlerConfig": {
            "query": {},
            "output_type": "database",
            "dst_db_table": DST_DB_TABLE,
        },
        "handlerData": {"data": "response_from_query"},
        "messageSource": "manual",
        "startTime": 1688821684,
    },
    {
        "handlerName": "ToolGetGroups2",
        "handlerConfig": {
            "query": {},
            "output_type": "rabbitmq",
            "dst_queue_name": DST_QUEUE_NAME,
        },
        "handlerData": {"data": "response_from_query2"},
        "messageSource": "manual",
        "startTime": 1688821689,
    },
]


class TotallyLegitNetConnFinding(VoltronFinding):
    """We take a single entry from the log data and convert it into a VoltronFinding"""

    def processPayload(self, payload: dict) -> dict:
        results = {
            "toolName": "TotallyLegitSiteNetConns",
            "resourceType": "host",
            "resourceId": payload["source"],
            # We're generating our own finding id, because the API doesn't give you one
            "toolFindingId": self._get_finding_id(payload),
            "toolFindingSummary": "Suspicious network connection from {} to {}".format(
                payload["source"], payload["destination"]
            ),
            "toolFindingJson": json.dumps(payload),
            "toolFindingURL": "NotSet",
            "toolFindingSeverity": "NotSet",
            # We can create our own function to change severity here, although the preference would be to perform the upgrade elsewhere
            "voltronSeverity": self._get_finding_severity(payload),
            "extractDate": helpers.get_time(),
            "findingDate": datetime.datetime.fromtimestamp(payload["time"]).isoformat(),
        }
        return results

    def _get_finding_id(self, payload: dict) -> str:
        json_data = json.dumps(payload, sort_keys=True)
        sha256_hash = hashlib.sha256(json_data.encode()).hexdigest()
        return sha256_hash

    def _get_finding_severity(self, payload: dict) -> str:
        response = "NotSet"
        if payload["port"] == 3389:
            logger.warning("Upgrading severity of finding.\n{}".format(payload))
            response = "High"
        return response


class TotallyLegitSiteQueryHandler(VoltronBaseQueryInterface):
    """Example Query Handler for getting responses from https://interview.totallylegitsite.com"""

    def __init__(self, endpoint: str = "https://interview.totallylegitsite.com/basic"):
        self.endpoint = endpoint
        self.session = self.gen_session()

    def gen_session(self):
        return requests.Session()

    def run_query(
        self,
        query_message: VoltronMessagePayload,
        session: Optional[requests.Session] = None,
    ) -> VoltronBaseProcessResponse:
        if session is None:
            session = self.session
        results = {"success": True, "message": "", "data": {}}
        try:
            response = session.get(self.endpoint)
            response.raise_for_status()
            data = response.json()["data"]
            results["message"] = "Got {} records".format(len(data))
            results["data"] = {"logs": data}

        except KeyError:
            logger.error("No data received.")
            results["succes"] = False
            results["message"] = "No data received"

        except requests.exceptions.RequestException as e:
            logger.error(e)
            results["succes"] = False
            results["message"] = str(e)

        return results

    def process_results(
        self, results: VoltronBaseProcessResponse
    ) -> VoltronBaseProcessResponse:
        """For this example, we will log events directly into a 'VoltronFinding' object that can be stored into a database.
        We COULD convert them into a message instead, and write them to another queue.
        You should create a 'type' key in the data object to specify whether this is a message or a finding
        """
        finding_list = []
        for entry in results["data"].get("logs", []):
            finding_list.append(TotallyLegitNetConnFinding(entry))
        results = {
            "success": True,
            "message": "",
            "data": {"type": "VoltronFindings", "VoltronFindings": finding_list},
        }
        return results


class TotallyLegitSiteQueueHandler(VoltronRabbitMQQueue):
    """Example Queue Handler for managing responses from https://interview.totallylegitsite.com"""

    def set_handlers(
        self, psql_handler: VoltronPostgres, query_handler: TotallyLegitSiteQueryHandler
    ):
        self.psql_handler = psql_handler
        self.query_handler = query_handler

    def process_message(
        self, ch, method, properties, body
    ) -> VoltronBaseProcessResponse:
        """Verify the message should be processed, run the query, write results"""
        response = {
            "success": False,
            "message": "Message not processed. No rule match",
            "data": {"body": body},
        }
        message = json.loads(body)
        if message["handlerName"] == "TotallyLegitSiteQueryHandler":
            try:
                logger.info("Processing message!")
                results = self.query_handler.run_query(VoltronMessagePayload)
                processed = self.query_handler.process_results(results)
                findings = [
                    tuple(x.findingOutput().values())
                    for x in processed["data"]["VoltronFindings"]
                ]
                self.psql_handler.write_to_table(
                    message["handlerConfig"]["dst_db_table"],
                    findings,
                    onConflict="(toolFindingId) DO UPDATE SET extractdate = EXCLUDED.extractdate",
                )
                response["success"] = True
                response["message"] = "Processed {} findings".format(len(findings))
                logger.info(response)
            except KeyError as e:
                logger.error(e)
                response["message"] = "Error : {}".format(e)
            except Exception as e:
                logger.error(e)
                response["message"] = "Error : {}".format(e)
        if response["success"]:
            # Super important. You must acknowledge the message or it will return to the queue
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(response)
        else:
            logger.error(response)


if __name__ == "__main__":
    logger.setLevel(logging.ERROR)

    logger.error("Creating Handlers\n")
    srcq_handler = TotallyLegitSiteQueueHandler(SRC_QUEUE_NAME, SRC_QUEUE_HOST, {})
    dstq_handler = TotallyLegitSiteQueueHandler(DST_QUEUE_NAME, DST_QUEUE_HOST, {})

    query_handler = TotallyLegitSiteQueryHandler()

    db_handler = VoltronDB(
        DST_DB_HOST, DST_DB_USER, DST_DB_PASSWORD, DST_DB_PORT, DST_DB_NAME
    )

    logger.error("Setup - Ensuring database tables exist\n")
    db_setup = VoltronDB(
        DST_DB_HOST, DST_DB_USER, DST_DB_PASSWORD, DST_DB_PORT, DST_DB_NAME
    )
    db_setup.create_tables()

    logger.error("Setup - Sending messages for later consumption:\n")
    setup_queue_handler = VoltronRabbitMQQueue(SRC_QUEUE_NAME, SRC_QUEUE_HOST, {})
    with setup_queue_handler.get_client() as client:
        for msg in sample_messages:
            asyncio.run(setup_queue_handler.send_message(msg, client))

    # logger.error("Demo - Just go run the query to prove it works\n")
    # raw_results = query_handler.run_query({})

    # logger.error("Demo - Read API and Write to Database\n")
    # raw_results = query_handler.run_query({})
    # formatted_results = query_handler.process_results(raw_results)
    # new_rows = [ tuple(x.findingOutput().values()) for x in formatted_results["data"]["VoltronFindings"]]
    # db_handler.write_to_table(DST_DB_TABLE, new_rows, onConflict='(toolFindingId) DO UPDATE SET extractdate = EXCLUDED.extractdate')

    logger.error("Demo - Read Queue, Run Query, Write to Database\n")
    # Configure in sql handler and query handler for the queue
    srcq_handler.set_handlers(db_handler, query_handler)
    srcq_client = srcq_handler.get_client()

    srcq_handler.handle_messages(srcq_client)
