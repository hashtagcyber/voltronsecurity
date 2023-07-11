from voltronsecurity.voltron_base import (
    VoltronBaseProcessResponse,
    VoltronMessagePayload,
    VoltronBaseMessageInterface,
)

from typing import Optional

import logging
import json
import pika

FORMAT = "[%(filename)s:%(lineno)s - %(funcName)s() ] %(message)s"
logging.basicConfig(format=FORMAT)
logger = logging.getLogger("voltron")


class VoltronRabbitMQQueue(VoltronBaseMessageInterface):
    def __init__(
        self,
        queue_name: str,
        queue_endpoint: str,
        credential: Optional[dict[str, str]] = None,
    ):
        self.queue_name = queue_name
        self.queue_endpoint = queue_endpoint
        self.creds = credential

    def get_client(
        self, queue_endpoint: Optional[str] = None, creds: Optional[dict] = None
    ) -> pika.BlockingConnection:
        if queue_endpoint is None:
            queue_endpoint = self.queue_endpoint
        if creds is None:
            creds = self.creds
        client = pika.BlockingConnection(pika.ConnectionParameters(host=queue_endpoint))
        return client

    def process_message(
        self, ch, method, properties, body
    ) -> VoltronBaseProcessResponse:
        """Callback method. Override in child class."""
        result = {
            "success": True,
            "message": "Default RabbitMQ Response. Message Dropped.",
            "data": {},
        }
        return result

    def handle_messages(
        self,
        client: Optional[pika.BlockingConnection] = None,
        queue: Optional[str] = None,
    ):
        # action = function_that_does_things  # params of ch, method, properties, body
        if client is None:
            client = self.get_client()
        if queue is None:
            queue = self.queue_name
        channel = client.channel()
        try:
            channel.queue_declare(queue=queue, arguments={"x-queue-mode": "lazy"})
            channel.basic_consume(
                queue=queue, on_message_callback=self.process_message, auto_ack=False
            )
            channel.start_consuming()
        except Exception as e:
            logger.error(e)
        channel.cancel()
        channel.close()

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
        message = json.dumps(body)
        return message

    async def send_message(
        self,
        message: VoltronMessagePayload,
        client: Optional[pika.BlockingConnection] = None,
        queue: Optional[str] = None,
    ) -> VoltronBaseProcessResponse:
        if client is None:
            client = self.get_client()
        if queue is None:
            queue = self.queue_name
        formatted = self.generate_message(
            message["handlerName"],
            message["handlerConfig"],
            message["handlerData"],
            message["messageSource"],
            message["startTime"],
        )
        channel = client.channel()
        channel.queue_declare(queue=queue, arguments={"x-queue-mode": "lazy"})
        try:
            channel.basic_publish(exchange="", routing_key=queue, body=formatted)
            response = {
                "success": True,
                "message": "Sent message.",
            }
        except Exception as e:
            response = {"success": False, "message": str(e)}
        return response
