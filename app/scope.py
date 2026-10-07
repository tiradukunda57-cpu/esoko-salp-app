def check_area(conn, actor, location_id):
    """Agents may only act inside their own sector. Admin/SuperAdmin have no area limit."""
    if actor["role"] in ("superadmin", "admin"):
        return
    if actor["role"] != "agent":
        raise PermissionError("forbidden")
    if actor["location_id"] is None:
        raise PermissionError("agent_has_no_area")
    a = conn.execute("SELECT sector,district FROM locations WHERE id=?", (actor["location_id"],)).fetchone()
    p = conn.execute("SELECT sector,district FROM locations WHERE id=?", (location_id,)).fetchone() if location_id else None
    if not p or (a["sector"], a["district"]) != (p["sector"], p["district"]):
        raise PermissionError("outside_agent_area")
