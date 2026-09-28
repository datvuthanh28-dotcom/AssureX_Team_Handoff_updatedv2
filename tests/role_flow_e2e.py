#!/usr/bin/env python3
"""End-to-end role-flow smoke tests for the running AssureX API."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

BASE = "http://127.0.0.1:8000"
PASSWORD = "TestPass123!"


class ApiError(RuntimeError):
    def __init__(self, method: str, path: str, status: int, body: str):
        super().__init__(f"{method} {path} -> HTTP {status}: {body[:500]}")
        self.status = status
        self.body = body


def request(method: str, path: str, *, token: str | None = None, data=None, expected=(200,)):
    body = None
    headers = {"Accept": "application/json"}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            if resp.status not in expected:
                raise ApiError(method, path, resp.status, raw)
            if not raw:
                return None
            if resp.headers.get_content_type() == "application/json":
                return json.loads(raw)
            return raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        if exc.code in expected:
            return json.loads(raw) if raw and raw[:1] in "[{" else raw
        raise ApiError(method, path, exc.code, raw) from exc


def ok(name: str, detail: str = ""):
    suffix = f" — {detail}" if detail else ""
    print(f"PASS {name}{suffix}")


def login_workspace(username: str, password: str) -> str:
    data = request("POST", "/api/auth/workspace/login", data={"username": username, "password": password})
    return data["access_token"]


def login_customer(email: str, password: str) -> str:
    data = request("POST", "/api/auth/login", data={"email": email, "password": password})
    return data["access_token"]


def register_or_login_customer(email: str) -> str:
    try:
        data = request("POST", "/api/auth/register", data={"email": email, "password": PASSWORD}, expected=(201,))
        return data["access_token"]
    except ApiError as exc:
        if exc.status != 409:
            raise
    return login_customer(email, PASSWORD)


def ensure_workspace_user(admin_token: str, username: str, email: str, role: str) -> str:
    payload = {"username": username, "email": email, "password": PASSWORD, "role": role}
    try:
        request("POST", "/api/auth/users", token=admin_token, data=payload, expected=(201,))
    except ApiError as exc:
        if exc.status != 409:
            raise
    return login_workspace(username, PASSWORD)


def first_product(token: str):
    products = request("GET", "/api/products", token=token)
    if not products:
        raise RuntimeError("No seeded products available; cannot register a customer product.")
    return products[0]


def register_product(token: str, product_id: int) -> dict:
    unique = int(time.time() * 1000)
    payload = {
        "product_id": product_id,
        "serial_number": f"E2E-SN-{unique}",
        "purchase_date": (date.today() - timedelta(days=45)).isoformat(),
        "purchase_price": 799.0,
        "retailer": "AssureX Authorized Dealer",
    }
    return request("POST", "/api/products/register", token=token, data=payload, expected=(201,))


def run():
    request("GET", "/health")
    ok("backend health")

    admin_token = login_workspace("admin", "123")
    reviewer_token = login_workspace("reviewer", "reviewer123")
    reviewer_stamp = int(time.time())
    created_reviewer = request(
        "POST",
        "/api/auth/users",
        token=admin_token,
        data={"username": f"reviewer_e2e_{reviewer_stamp}", "email": f"reviewer.e2e.{reviewer_stamp}@assurex.local", "password": PASSWORD, "role": "REVIEWER"},
        expected=(201,),
    )
    assert created_reviewer["role"] == "REVIEWER"
    request(
        "POST",
        "/api/auth/users",
        token=admin_token,
        data={"username": "service_e2e_blocked", "email": "service.e2e.blocked@assurex.local", "password": PASSWORD, "role": "SERVICE_CENTER"},
        expected=(422,),
    )
    ok("workspace logins", "ADMIN, REVIEWER; admin creation is limited to REVIEWER")

    stamp = int(time.time())
    customer_email = f"customer.e2e.{stamp}@assurex.local"
    customer_token = register_or_login_customer(customer_email)
    other_customer_token = register_or_login_customer(f"other.e2e.{stamp}@assurex.local")
    ok("customer registration/login")

    request("GET", "/api/auth/users", token=reviewer_token, expected=(403,))
    request("GET", "/api/retraining/dataset", expected=(401, 403))
    ok("negative authorization", "reviewer/admin-only, public retraining, non-reviewer creation blocked")

    product = first_product(customer_token)
    registered = register_product(customer_token, product["id"])
    product_code = registered["registration_code"]
    looked_up = request("GET", f"/api/claims/v3/product/{urllib.parse.quote(product_code)}", token=customer_token)
    assert looked_up["registration_code"] == product_code
    ok("customer product registration", product_code)

    request(
        "POST",
        "/api/claims/v3/ticket",
        token=customer_token,
        data={
            "product_code": product_code,
            "incident_date": (date.today() - timedelta(days=1)).isoformat(),
            "problem_category": "Other",
            "fault_description": "",
            "previous_repair": "No",
            "purchase_invoice_available": "Yes",
            "serial_image_available": "Yes",
            "fault_evidence_available": "Yes",
            "repair_report_available": "No",
        },
        expected=(422,),
    )
    ok("other category validation", "description required only for Other")

    ticket_payload = {
        "product_code": product_code,
        "incident_date": (date.today() - timedelta(days=2)).isoformat(),
        "problem_category": "Power Failure",
        "fault_description": "",
        "previous_repair": "No",
        "purchase_invoice_available": "Yes",
        "serial_image_available": "Yes",
        "fault_evidence_available": "Yes",
        "repair_report_available": "No",
    }
    ticket_result = request("POST", "/api/claims/v3/ticket", token=customer_token, data=ticket_payload, expected=(201,))
    ticket = ticket_result["ticket"]
    ticket_id = ticket["ticket_id"]
    assert len(ticket["model_features"]) == 14, ticket["model_features"]
    ok("customer warranty ticket submission", f"{ticket_id} via {ticket['model_version']}")

    request("GET", f"/api/customer/claims/{ticket_id}", token=other_customer_token, expected=(404,))
    own_claim = request("GET", f"/api/customer/claims/{ticket_id}", token=customer_token)
    assert own_claim["claim_id"] == ticket_id
    assert own_claim["decision"]["ml_prediction"] == "Valid Claim", own_claim
    assert own_claim["status"] == "Waiting to proceed", own_claim
    ok("customer claim isolation", "WARRANTY prediction shows Waiting to proceed")

    queue = request("GET", "/api/warranty/reviewer/tickets?status_filter=WAITING_REVIEW", token=reviewer_token)
    assert any(row["ticket_id"] == ticket_id for row in queue["tickets"]), queue
    detail = request("GET", f"/api/warranty/reviewer/tickets/{ticket_id}", token=reviewer_token)
    assert detail["ticket"]["ticket_id"] == ticket_id
    ok("reviewer queue/detail")

    request("POST", f"/api/warranty/reviewer/tickets/{ticket_id}/decision", token=customer_token, data={"decision": "APPROVE"}, expected=(403,))
    reviewed = request(
        "POST",
        f"/api/warranty/reviewer/tickets/{ticket_id}/decision",
        token=reviewer_token,
        data={"decision": "APPROVE", "reviewer_note": "Evidence and active warranty satisfy the policy."},
    )
    assert reviewed["ticket"]["status"] == "REVIEWED"
    ok("reviewer final decision", reviewed["ticket"]["ground_truth"])

    customer_claim_after = request("GET", f"/api/customer/claims/{ticket_id}", token=customer_token)
    assert customer_claim_after["status"] == "Approved", customer_claim_after
    ok("customer sees reviewer outcome", customer_claim_after["status"])

    export = request("GET", "/api/warranty/reviewer/export/retraining-dataset?format=json", token=reviewer_token)
    assert any(row["ClaimID"] == ticket_id and row["ClaimClass"] == "Valid Claim" for row in export["data"]), export
    retraining = request("GET", "/api/retraining/dataset", token=reviewer_token)
    assert any(row["ClaimID"] == ticket_id for row in retraining["data"]), retraining
    ok("reviewer retraining export")

    admin_claims = request("GET", "/api/customer/claims", token=admin_token)
    assert any(row["claim_id"] == ticket_id for row in admin_claims), admin_claims
    audit = request("GET", "/api/audit", token=admin_token)
    assert isinstance(audit, list)
    ok("admin monitoring/audit")

    print("ROLE_FLOW_E2E_PASS")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"ROLE_FLOW_E2E_FAIL: {exc}", file=sys.stderr)
        raise
