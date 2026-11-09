#!/usr/bin/env python3
"""
MCP Server Entrypoint for Smart Farm Management AI Agent System.
Provides MCP Resources and Tools for Multi-Pen Management, Animal Transfer, IoT & Environment Monitoring.
"""

from app.mcp.mcp_server import (
    mcp,
    transfer_animal_pen,
    get_pen_status,
    manage_pen,
    control_device,
    log_feeding,
    update_animal_health,
    manage_inventory,
    manage_schedule,
    create_system_alert,
    get_farm_overview,
    get_pens_list,
    get_latest_env_logs,
    get_low_stock_inventory,
    get_animals_attention,
    get_crops_harvest,
)

if __name__ == "__main__":
    mcp.run()
