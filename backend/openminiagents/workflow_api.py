"""API for General workflow generic sub-agent catalog and settings."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .workflow_settings import settings_for_api, update_workflow_settings

router = APIRouter(tags=["workflow"])


class UpdateWorkflowSettingsBody(BaseModel):
    enabled_generic_agents: list[str] = Field(default_factory=list)


@router.get("/workflow/generic-agents")
async def list_generic_agents() -> dict:
    from workflow_agent.generic_agents.catalog import get_catalog_for_api

    return {"agents": get_catalog_for_api()}


@router.get("/workflow/settings")
async def get_settings() -> dict:
    return {"settings": settings_for_api()}


@router.put("/workflow/settings")
async def put_settings(body: UpdateWorkflowSettingsBody) -> dict:
    update_workflow_settings(enabled_generic_agents=body.enabled_generic_agents)
    from .runner_bridge import get_runner_bridge

    get_runner_bridge().clear_runner_cache()
    return {"settings": settings_for_api()}
