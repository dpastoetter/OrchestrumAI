#!/usr/bin/env python3
"""Minimal CLI for OrchestrumAI REST API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = os.environ.get("ORCHESTRUMAI_API", "http://127.0.0.1:8000/api")


def _request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{DEFAULT_BASE.rstrip('/')}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {detail}", file=sys.stderr)
        sys.exit(1)


def cmd_health(_: argparse.Namespace) -> None:
    print(json.dumps(_request("GET", "/health"), indent=2))


def cmd_list_requests(_: argparse.Namespace) -> None:
    items = _request("GET", "/requests")
    for r in items:
        print(f"{r['id'][:8]}… {r['status']:18} {r['title']}")


def cmd_run_template(args: argparse.Namespace) -> None:
    body: dict = {}
    if args.title:
        body["title"] = args.title
    if args.var:
        vars_map = {}
        for pair in args.var:
            if "=" in pair:
                k, v = pair.split("=", 1)
                vars_map[k] = v
        body["description_vars"] = vars_map
    summary = _request("POST", f"/workflow-templates/{args.template_id}/run", body)
    print(f"Created request {summary['id']} — {summary.get('status', '')}")


def cmd_submit(args: argparse.Namespace) -> None:
    body = {
        "title": args.title,
        "description": args.description,
        "priority": args.priority,
        "agent_type": args.agent_type,
    }
    summary = _request("POST", "/requests", body)
    print(f"Created request {summary['id']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="OrchestrumAI CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health", help="GET /api/health").set_defaults(func=cmd_health)
    sub.add_parser("list", help="List requests").set_defaults(func=cmd_list_requests)

    run_p = sub.add_parser("run", help="Run a workflow template")
    run_p.add_argument("template_id", help="Template UUID")
    run_p.add_argument("--title", default="")
    run_p.add_argument("--var", action="append", default=[], help="key=value custom var")
    run_p.set_defaults(func=cmd_run_template)

    sub_p = sub.add_parser("submit", help="Submit a JSON workflow request")
    sub_p.add_argument("--title", required=True)
    sub_p.add_argument("--description", required=True)
    sub_p.add_argument("--priority", default="normal", choices=["low", "normal", "high"])
    sub_p.add_argument("--agent-type", default="workflow", dest="agent_type")
    sub_p.set_defaults(func=cmd_submit)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
