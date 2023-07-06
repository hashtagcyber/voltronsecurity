import asyncio
import datetime
import unittest
import json
from unittest import mock
from src.voltronsecurity.voltron_azure import (
    VoltronAzureServiceBusQueue,
    DefaultAzureCredential,
    ServiceBusClient,
    ServiceBusMessage,
)
from azure.servicebus.aio import ServiceBusReceiver, ServiceBusSender


class TestVoltronAzureServiceBusQueue(unittest.TestCase):
    def setUp(self) -> None:
        self.sample_queue_name = "mytestqueue"
        self.sample_namespace = "mytestnamespace"
        self.sample_creds = mock.MagicMock(spec=DefaultAzureCredential)
        self.sample_voltron_payload = {
            "handlerName": "samplehandler",
            "handlerConfig": {},
            "handlerData": {},
            "messageSource": "test_voltron_azure.py",
            "startTime": 12345,
        }
        self.sample_received_messages = [
            ServiceBusMessage(json.dumps(self.sample_voltron_payload))
        ]

    @mock.patch(
        "src.voltronsecurity.voltron_azure.ServiceBusClient",
        return_value=mock.AsyncMock(),
    )
    def test_init(self, mock_sbc):
        handler = VoltronAzureServiceBusQueue(
            self.sample_queue_name, self.sample_namespace, self.sample_creds
        )
        self.assertEqual(self.sample_queue_name, handler.queue_name)
        self.assertEqual(self.sample_namespace, handler.namespace)
        self.assertEqual(type(self.sample_creds), type(handler.creds))

    @mock.patch(
        "src.voltronsecurity.voltron_azure.ServiceBusClient",
        return_value=mock.AsyncMock(),
    )
    def test_happy_default_get_client(self, mock_sbc):
        handler = VoltronAzureServiceBusQueue(
            self.sample_queue_name, self.sample_namespace, self.sample_creds
        )
        client = handler.get_client()
        mock_sbc.assert_called_with(self.sample_namespace, self.sample_creds)

    @mock.patch("src.voltronsecurity.voltron_azure.ServiceBusClient")
    def test_happy_default_handle_messages(self, mock_sbc):
        mock_sbr = mock.AsyncMock(spec=ServiceBusReceiver)
        mock_sbr.return_value.__aenter__.return_value = mock_sbr.return_value
        mock_sbr.return_value.__aexit__.return_value = None
        mock_sbr.receive_messages.return_value = self.sample_received_messages

        mock_sbc.return_value.get_queue_receiver.return_value = mock_sbr
        handler = VoltronAzureServiceBusQueue(
            self.sample_queue_name, self.sample_namespace, self.sample_creds
        )
        resp = asyncio.run(handler.handle_messages())
        mock_sbr.complete_message.assert_called()

    @mock.patch(
        "src.voltronsecurity.voltron_azure.VoltronAzureServiceBusQueue.process_message",
        return_value={"success": False, "message": "MockedFail", "data": {}},
    )
    @mock.patch("src.voltronsecurity.voltron_azure.ServiceBusClient")
    def test_failed_process_messages(self, mock_sbc, mock_vsb):
        mock_sbr = mock.AsyncMock(spec=ServiceBusReceiver)
        mock_sbr.return_value.__aenter__.return_value = mock_sbr.return_value
        mock_sbr.return_value.__aexit__.return_value = None
        mock_sbr.receive_messages.return_value = self.sample_received_messages

        mock_sbc.return_value.get_queue_receiver.return_value = mock_sbr
        handler = VoltronAzureServiceBusQueue(
            self.sample_queue_name, self.sample_namespace, self.sample_creds
        )
        resp = asyncio.run(handler.handle_messages())
        mock_sbr.complete_message.assert_not_called()
        self.assertIn("success", resp[0])
        self.assertIn("message", resp[0])
        self.assertIn("data", resp[0])
        self.assertEqual(resp[0]["success"], False)

    def test_generate_message(self):
        handler = VoltronAzureServiceBusQueue(
            self.sample_queue_name, self.sample_namespace, self.sample_creds
        )
        msg_h_name = "samplehandlerName"
        msg_h_config = {}
        msg_h_data = {}
        msg_source = "samplemessageSource"
        msg_start_time = 1234

        new_message = handler.generate_message(
            msg_h_name, msg_h_config, msg_h_data, msg_source, msg_start_time
        )
        msg_json = json.loads(str(new_message))

        self.assertEqual(type(new_message), ServiceBusMessage)
        self.assertEqual(msg_json["handlerName"], msg_h_name)
        self.assertEqual(msg_json["handlerConfig"], msg_h_config)
        self.assertEqual(msg_json["handlerData"], msg_h_data)
        self.assertEqual(msg_json["messageSource"], msg_source)
        self.assertEqual(msg_json["startTime"], msg_start_time)

    @mock.patch("src.voltronsecurity.voltron_azure.ServiceBusClient")
    def test_happy_default_send_message(self, mock_sbc):
        mock_sbs = mock.AsyncMock(spec=ServiceBusSender)
        mock_sbs.return_value.__aenter__.return_value = mock_sbs.return_value
        mock_sbs.return_value.__aexit__.return_value = None
        mock_sbs.send_messages.return_value = None

        mock_sbc.return_value.get_queue_sender.return_value = mock_sbs
        handler = VoltronAzureServiceBusQueue(
            self.sample_queue_name, self.sample_namespace, self.sample_creds
        )
        resp = asyncio.run(handler.send_message(self.sample_voltron_payload))
        self.assertIn("success", resp)
        self.assertIn("message", resp)
        self.assertEqual(resp["success"], True)

    @mock.patch("src.voltronsecurity.voltron_azure.ServiceBusClient")
    def test_failed_default_send_message(self, mock_sbc):
        mock_sbs = mock.AsyncMock(spec=ServiceBusSender)
        mock_sbs.return_value.__aenter__.return_value = mock_sbs.return_value
        mock_sbs.return_value.__aexit__.return_value = None
        mock_sbs.send_messages.side_effect = Exception("TestSendFailure")

        mock_sbc.return_value.get_queue_sender.return_value = mock_sbs
        handler = VoltronAzureServiceBusQueue(
            self.sample_queue_name, self.sample_namespace, self.sample_creds
        )
        resp = asyncio.run(handler.send_message(self.sample_voltron_payload))
        self.assertIn("success", resp)
        self.assertIn("message", resp)
        self.assertEqual(resp["success"], False)
        self.assertEqual(resp["message"], "TestSendFailure")
