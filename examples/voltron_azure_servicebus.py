import asyncio
import logging
import os
import time

from voltronsecurity import voltron_azure
from azure.core.credentials import AzureSasCredential

FORMAT = "[%(filename)s:%(lineno)s - %(funcName)s() ] %(message)s"
logging.basicConfig(format=FORMAT)
logger = logging.getLogger("voltron_azure_example")

if __name__ == "__main__":
    logger.setLevel("DEBUG")
    logger.debug("Getting Environs")
    try:
        VOLTRON_ASB_QUEUE = os.environ["VOLTRON_QUEUE"]
        VOLTRON_ASB_NAMESPACE = os.environ["VOLTRON_ASB_NAMESPACE"]
    except KeyError as e:
        logger.error("Required environment variable {} not set".format(e))
        raise SystemExit(1)

    logger.debug("Setting Creds")
    # creds = voltron_azure.DefaultAzureCredential()
    creds = AzureSasCredential(os.environ.get("AZUREBOOM"))

    logger.debug("Creating Queue Handler")
    voltbus = voltron_azure.VoltronAzureServiceBusQueue(
        VOLTRON_ASB_QUEUE, VOLTRON_ASB_NAMESPACE, creds
    )

    sample_message = {
        "handlerName": "samplehandler",
        "handlerConfig": {},
        "handlerData": {},
        "messageSource": "voltron_azure.py",
        "startTime": int(time.time()),
    }
    logger.debug("Sample Message:\n\t{}".format(sample_message))
    logger.debug("Writing message to queue")
    send_results = asyncio.run(voltbus.send_message(sample_message))
    logger.debug(send_results)

    logger.debug("Getting messages from queue")
    results = asyncio.run(voltbus.handle_messages())
    logger.debug(results)
