"""Hotel Operations local MCP Server.

This server exposes PMS (Property Management System) operational tools to the ADK agent.
Each tool reads from `data/hotel_state.json`. Before any returned dictionaries are passed
to the standard I/O (stdio) transport, their text contents are run through the `clean_data()`
sanitizer to ensure no sensitive customer PII or potential prompt injection commands
leak into the model context.
"""

import json
import os
from datetime import date, datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server.security import redact_pii, screen_for_injection

# Initialize the FastMCP wrapper using standard input/output transport
mcp = FastMCP("Hotel Operations Server")

# Resolve absolute path to the local PMS state json file
DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "hotel_state.json",
)


def load_hotel_state() -> dict:
    """Helper to load hotel state JSON from disk."""
    with open(DATA_PATH) as f:
        return json.load(f)


def clean_data(data: Any) -> Any:
    """Recursively clean sensitive data from free-text fields.

    This ensures fields like guest comment or issue description are sanitized
    prior to returning. This central function enforces the data security boundary.
    """
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if k in (
                "guest_comment",
                "guest_remarks",
                "comment",
                "issue_description",
            ) and isinstance(v, str):
                cleaned[k] = screen_for_injection(redact_pii(v))
            else:
                cleaned[k] = clean_data(v)
        return cleaned
    elif isinstance(data, list):
        return [clean_data(item) for item in data]
    return data


@mcp.tool()
def get_occupancy_summary() -> dict:
    """Get the current room occupancy statistics and guest comments.

    Returns metrics including total, occupied, and available rooms, today's arrivals,
    and returns a list of comments for current or upcoming (within 3 days) guests
    to help managers plan arrivals. All comments are sanitized.
    """
    state = load_hotel_state()
    rooms = state.get("rooms", [])
    total_rooms = len(rooms)

    # Calculate current occupancy state from reservations list
    reservations = state.get("reservations", [])
    occupied_rooms = len([r for r in reservations if r.get("status") == "in_house"])
    reservations_today = len(
        [r for r in reservations if r.get("status") == "arriving_today"]
    )
    departures_today = len(
        [r for r in reservations if r.get("status") == "departing_today"]
    )
    available_rooms = total_rooms - occupied_rooms

    # Today is anchored to 2026-06-30 for simulation stability
    current_date = date(2026, 6, 30)

    guest_comments = []
    for r in reservations:
        status = r.get("status")
        include = False

        if status in ("in_house", "arriving_today"):
            include = True
        elif status == "upcoming":
            # Check if arrival date is within next 3 days
            arrival_str = r.get("arrival_date")
            if arrival_str:
                try:
                    arrival_date = datetime.strptime(arrival_str, "%Y-%m-%d").date()
                    delta = (arrival_date - current_date).days
                    if 0 <= delta <= 3:
                        include = True
                except ValueError:
                    pass

        if include:
            guest_comments.append(
                {
                    "guest_name": r.get("guest_name"),
                    "room_number": r.get("room_number"),
                    "status": status,
                    "guest_comment": r.get("guest_comment"),
                }
            )

    return clean_data(
        {
            "total_rooms": total_rooms,
            "occupied_rooms": occupied_rooms,
            "available_rooms": available_rooms,
            "reservations_today": reservations_today,
            "departures_today": departures_today,
            "guest_comments": guest_comments,
        }
    )


@mcp.tool()
def get_housekeeping_status() -> dict:
    """Aggregate room status counts across all rooms.

    Provides the agent with a complete operational summary of housekeeping categories
    (clean, dirty, inspected, out_of_order, in_progress) without overloading context
    with individual room records.
    """
    state = load_hotel_state()
    rooms = state.get("rooms", [])

    counts = {}
    for r in rooms:
        status = r.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1

    return counts


@mcp.tool()
def get_room_details(room_number: int) -> dict:
    """Inspect status, housekeeping tasks, and maintenance tickets for a specific room.

    Added as an iteration fix: this single-point tool enables the agent to cross-reference
    specific room anomalies (e.g. VIP guest assigned to out-of-order room 404) directly.
    """
    state = load_hotel_state()
    rooms = state.get("rooms", [])
    
    room_info = {}
    for r in rooms:
        if r.get("room_number") == room_number:
            room_info = dict(r)
            break
            
    if not room_info:
        return {"error": f"Room {room_number} not found."}
        
    # Check housekeeping tasks
    tasks = state.get("housekeeping_tasks", [])
    room_info["housekeeping_task"] = next((t for t in tasks if t.get("room_number") == room_number), None)
    
    # Check open maintenance tickets
    tickets = state.get("maintenance_tickets", [])
    room_info["maintenance_tickets"] = [t for t in tickets if t.get("room_number") == room_number]
    
    return clean_data(room_info)


@mcp.tool()
def get_maintenance_tickets(status_filter: str | None = None) -> list:
    """Get active maintenance tickets, optionally filtered by status.

    Returns the ticket lists containing room numbers, descriptions, and priorities.
    Helps the agent check for open issues that conflict with guest arrivals.
    """
    state = load_hotel_state()
    tickets = state.get("maintenance_tickets", [])
    if status_filter:
        tickets = [t for t in tickets if t.get("status") == status_filter]
    return clean_data(tickets)


@mcp.tool()
def get_staffing_levels() -> list:
    """Get the full list of staff shift schedules and current status.

    Returns roster details (name, role, shift, status) enabling the agent to detect
    if off-duty staff members have been assigned active cleaning/maintenance tasks.
    """
    state = load_hotel_state()
    return clean_data(state.get("staffing", []))


if __name__ == "__main__":
    mcp.run()
