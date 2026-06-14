from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = (
    REPO_ROOT / "artifacts" / "workflows" / "n8n" / "fathiya-connector-gateway-v1.json"
)
CONNECTOR_PROFILES_PATH = (
    REPO_ROOT / "services" / "agent-runtime" / "config" / "connector_profiles.json"
)


class N8nConnectorWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.workflow = json.loads(self.text)
        self.nodes = {node["name"]: node for node in self.workflow["nodes"]}

    def test_workflow_is_inactive_and_local_only(self) -> None:
        self.assertEqual(self.workflow["id"], "FathiyaConnectorGatewayV1")
        self.assertFalse(self.workflow["active"])
        ingress = self.nodes["Local FATHIYA Ingress"]
        self.assertEqual(ingress["parameters"]["responseMode"], "responseNode")
        self.assertEqual(ingress["parameters"]["options"]["ipWhitelist"], "127.0.0.1,::1")

    def test_workflow_contains_the_expected_gate_nodes(self) -> None:
        expected_types = {
            "Local FATHIYA Ingress": "n8n-nodes-base.webhook",
            "Validate and Gate": "n8n-nodes-base.code",
            "Approval Granted?": "n8n-nodes-base.if",
            "Dispatch Approved Connector": "n8n-nodes-base.httpRequest",
            "Respond Dispatched": "n8n-nodes-base.respondToWebhook",
            "Respond Staged": "n8n-nodes-base.respondToWebhook",
        }
        self.assertEqual(
            {name: node["type"] for name, node in self.nodes.items()},
            expected_types,
        )

    def test_dispatch_is_reachable_only_from_approved_branch(self) -> None:
        validation_code = self.nodes["Validate and Gate"]["parameters"]["jsCode"]
        self.assertIn("approvalState === 'approved'", validation_code)
        self.assertIn("allowedProfiles", validation_code)
        self.assertIn("'n8n_health'", validation_code)
        self.assertIn("'n8n_workflows'", validation_code)
        self.assertNotIn("'n8n_fathiya_webhook'", validation_code)
        self.assertIn("query: body.query", validation_code)
        connector_profiles = json.loads(
            CONNECTOR_PROFILES_PATH.read_text(encoding="utf-8")
        )["profiles"]
        for profile in connector_profiles:
            quoted_name = f"'{profile['name']}'"
            if profile.get("bridge_dispatch_allowed"):
                self.assertIn(quoted_name, validation_code)
            else:
                self.assertNotIn(quoted_name, validation_code)

        approval_outputs = self.workflow["connections"]["Approval Granted?"]["main"]
        self.assertEqual(approval_outputs[0][0]["node"], "Dispatch Approved Connector")
        self.assertEqual(approval_outputs[1][0]["node"], "Respond Staged")
        inbound_nodes = {
            source
            for source, outputs in self.workflow["connections"].items()
            for branch in outputs["main"]
            for connection in branch
            if connection["node"] == "Dispatch Approved Connector"
        }
        self.assertEqual(inbound_nodes, {"Approval Granted?"})

    def test_dispatch_uses_environment_references_without_literal_target(self) -> None:
        dispatch = self.nodes["Dispatch Approved Connector"]["parameters"]
        self.assertEqual(dispatch["url"], "={{ $env.FATHIYA_CONNECTOR_DISPATCH_URL }}")
        self.assertIn("FATHIYA_CONNECTOR_DISPATCH_TOKEN", json.dumps(dispatch))
        self.assertIsNone(re.search(r"https?://", json.dumps(dispatch)))

    def test_workflow_contains_no_secret_value(self) -> None:
        self.assertNotIn("credentials", self.text)
        self.assertNotRegex(self.text, r"sk-or-v1-[A-Za-z0-9_-]{20,}")
        self.assertNotRegex(self.text, r"hooks\.zapier\.com/hooks/catch/")
        self.assertNotRegex(self.text, r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")


if __name__ == "__main__":
    unittest.main()
