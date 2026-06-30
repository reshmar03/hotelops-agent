import json
import os
from datetime import date, datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server.security import redact_pii, screen_for_injection

# Define the FastMCP server
mcp = FastMCP("Hotel Operations Server")

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "hotel_state.json",
)


def load_hotel_state() -> dict:
    """Helper to load hotel state JSON."""
    with open(DATA_PATH) as f:
        return json.load(f)


def clean_data(data: Any) -> Any:
    """Recursively clean free-text fields (guest_comment, issue_description) in data."""
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
    """Get the current room occupancy statistics and guest comments."""
    state = load_hotel_state()
    rooms = state.get("rooms", [])
    total_rooms = len(rooms)

    # Calculate occupancy from reservations and rooms
    reservations = state.get("reservations", [])
    occupied_rooms = len([r for r in reservations if r.get("status") == "in_house"])
    reservations_today = len(
        [r for r in reservations if r.get("status") == "arriving_today"]
    )
    departures_today = len(
        [r for r in reservations if r.get("status") == "departing_today"]
    )
    available_rooms = total_rooms - occupied_rooms

    # Hotel current date is 2026-06-30 (from JSON)
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
    """Get the housekeeping count breakdown for all statuses present in the data."""
    state = load_hotel_state()
    rooms = state.get("rooms", [])

    counts = {}
    for r in rooms:
        status = r.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1

    return counts


@mcp.tool()
def get_maintenance_tickets(status_filter: str | None = None) -> list:
    """Get maintenance tickets, optionally filtered by status ('open', 'closed', 'resolved', 'in_progress')."""
    state = load_hotel_state()
    tickets = state.get("maintenance_tickets", [])
    if status_filter:
        tickets = [t for t in tickets if t.get("status") == status_filter]
    return clean_data(tickets)


@mcp.tool()
def get_staffing_levels() -> dict:
    """Get current on-shift staffing levels by department."""
    state = load_hotel_state()
    staffing_list = state.get("staffing", [])

    levels = {}
    for member in staffing_list:
        if member.get("status") == "on_duty":
            role = member.get("role")
            levels[role] = levels.get(role, 0) + 1

    return levels


if __name__ == "__main__":
    mcp.run()
