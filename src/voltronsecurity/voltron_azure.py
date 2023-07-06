from voltronsecurity.voltron_base import (
    VoltronBaseProcessResponse,
    VoltronMessagePayload,
    VoltronBaseMessageInterface,
)
import logging
import json
import asyncio
import os
import time

from typing import Optional

from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage
from azure.identity.aio import DefaultAzureCredential

FORMAT = "[%(filename)s:%(lineno)s - %(funcName)s() ] %(message)s"
logging.basicConfig(format=FORMAT)
logger = logging.getLogger("voltron")


class VoltronAzureServiceBusQueue(VoltronBaseMessageInterface):
    def __init__(
        self, queue_name: str, namespace: str, credential: DefaultAzureCredential
    ):
        self.queue_name = queue_name
        self.namespace = namespace
        self.creds = credential

    def get_client(
        self, namespace: Optional[str] = None, creds: Optional[str] = None
    ) -> ServiceBusClient:
        if namespace is None:
            namespace = self.namespace
        if creds is None:
            creds = self.creds
        client = ServiceBusClient(namespace, creds)
        return client

    async def handle_messages(
        self, client: Optional[ServiceBusClient] = None, queue: Optional[str] = None
    ) -> list[VoltronBaseProcessResponse]:
        """Primary async loop for retrieving and processing messages.
        Awaits other class methods to perform an action on each message.
        """
        if queue is None:
            queue = self.queue_name
        if client is None:
            client = self.get_client()
        results = []
        async with client:
            receiver = client.get_queue_receiver(queue_name=queue)
            async with receiver:
                received = await receiver.receive_messages(
                    max_wait_time=5, max_message_count=1
                )
                for msg in received:
                    logger.debug(str(msg))
                    resp = await self.process_message(json.loads(str(msg)))
                    results.append(resp)
                    if resp["success"]:
                        await receiver.complete_message(msg)
                    else:
                        continue
        await self.creds.close()
        return results

    async def process_message(
        self, message: VoltronMessagePayload
    ) -> VoltronBaseProcessResponse:
        """Override this in child class to perform an action based on the message received."""
        logger.debug("Processed Message : {}".format(message))
        response = {
            "success": True,
            "message": "Default Message Processor. No action taken. Message deleted.",
            "data": message,
        }
        return response

    def generate_message(
        self,
        handlerName: str,
        handlerConfig: dict,
        handlerData: dict,
        messageSource: str,
        startTime: int,
    ) -> VoltronMessagePayload:
        body = {
            "handlerName": handlerName,
            "handlerConfig": handlerConfig,
            "handlerData": handlerData,
            "messageSource": messageSource,
            "startTime": startTime,
        }
        message = ServiceBusMessage(
            body=json.dumps(body), content_type="application/json"
        )
        return message

    async def send_message(
        self,
        message: VoltronMessagePayload,
        client: Optional[ServiceBusClient] = None,
        queue: Optional[str] = None,
    ) -> VoltronBaseProcessResponse:
        if queue is None:
            queue = self.queue_name
        if client is None:
            client = self.get_client()
        servicebus_message = self.generate_message(
            message["handlerName"],
            message["handlerConfig"],
            message["handlerData"],
            message["messageSource"],
            message["startTime"],
        )
        message_list = [servicebus_message]
        async with client:
            sender = client.get_queue_sender(queue_name=queue)
            async with sender:
                try:
                    await sender.send_messages(message_list)
                    response = {
                        "success": True,
                        "message": "Sent {} messages".format(len(message_list)),
                    }
                except Exception as e:
                    response = {"success": False, "message": str(e)}

        return response
