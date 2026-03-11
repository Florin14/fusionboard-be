import base64
from typing import Optional

from fastapi import HTTPException, Query
from fastapi.responses import Response

from modules.football_tracking.api_client import fetch
from .router import router

# Fields that contain large base64 images – strip from list responses
_IMAGE_FIELDS = {"avatar", "logo", "team1Logo", "team2Logo", "leagueLogo"}


@router.get("/stats")
async def get_stats():
    try:
        raw = fetch("/stats")
        return {
            "users": raw.get("totalUsers", 0),
            "players": raw.get("totalPlayers", 0),
            "teams": raw.get("totalTeams", 0),
            "matches": raw.get("totalMatches", 0),
            "goals": raw.get("totalGoals", 0),
            "tournaments": raw.get("totalTournaments", 0),
            "trainings": raw.get("totalTrainingSessions", 0),
        }
    except Exception as e:
        raise HTTPException(502, detail=f"Football API error: {e}")


@router.get("/users")
async def get_users(
    search: Optional[str] = None,
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    try:
        return fetch("/users", {"search": search, "limit": limit, "offset": offset})
    except Exception as e:
        raise HTTPException(502, detail=f"Football API error: {e}")


@router.get("/players")
async def get_players(
    teamId: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    try:
        rows = fetch("/players", {"teamId": teamId, "search": search, "limit": limit, "offset": offset})
        for row in rows:
            has_avatar = bool(row.get("avatar"))
            for f in _IMAGE_FIELDS:
                row.pop(f, None)
            row["hasAvatar"] = has_avatar
        return rows
    except Exception as e:
        raise HTTPException(502, detail=f"Football API error: {e}")


@router.get("/players/{player_id}/avatar")
async def get_player_avatar(player_id: int):
    """Serve player avatar as an image."""
    try:
        rows = fetch("/players", {"limit": 200})
        for p in rows:
            if p.get("id") == player_id and p.get("avatar"):
                img = base64.b64decode(p["avatar"])
                return Response(content=img, media_type="image/jpeg",
                                headers={"Cache-Control": "public, max-age=3600"})
        raise HTTPException(404, detail="Avatar not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, detail=f"Football API error: {e}")


@router.get("/teams")
async def get_teams(
    search: Optional[str] = None,
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    try:
        rows = fetch("/teams", {"search": search, "limit": limit, "offset": offset})
        for row in rows:
            has_logo = bool(row.get("logo"))
            for f in _IMAGE_FIELDS:
                row.pop(f, None)
            row["hasLogo"] = has_logo
        return rows
    except Exception as e:
        raise HTTPException(502, detail=f"Football API error: {e}")


@router.get("/teams/{team_id}/logo")
async def get_team_logo(team_id: int):
    """Serve team logo as an image."""
    try:
        rows = fetch("/teams", {"limit": 200})
        for t in rows:
            if t.get("id") == team_id and t.get("logo"):
                img = base64.b64decode(t["logo"])
                return Response(content=img, media_type="image/jpeg",
                                headers={"Cache-Control": "public, max-age=3600"})
        raise HTTPException(404, detail="Logo not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, detail=f"Football API error: {e}")


@router.get("/matches")
async def get_matches(
    teamId: Optional[int] = None,
    state: Optional[str] = None,
    leagueId: Optional[int] = None,
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    try:
        rows = fetch("/matches", {"teamId": teamId, "state": state, "leagueId": leagueId, "limit": limit, "offset": offset})
        for row in rows:
            has_t1 = bool(row.get("team1Logo"))
            has_t2 = bool(row.get("team2Logo"))
            for f in _IMAGE_FIELDS:
                row.pop(f, None)
            row["hasTeam1Logo"] = has_t1
            row["hasTeam2Logo"] = has_t2
        return rows
    except Exception as e:
        raise HTTPException(502, detail=f"Football API error: {e}")


@router.get("/goals")
async def get_goals(
    matchId: Optional[int] = None,
    playerId: Optional[int] = None,
    teamId: Optional[int] = None,
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    try:
        return fetch("/goals", {"matchId": matchId, "playerId": playerId, "teamId": teamId, "limit": limit, "offset": offset})
    except Exception as e:
        raise HTTPException(502, detail=f"Football API error: {e}")


@router.get("/tournaments")
async def get_tournaments(
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    try:
        return fetch("/tournaments", {"limit": limit, "offset": offset})
    except Exception as e:
        raise HTTPException(502, detail=f"Football API error: {e}")


@router.get("/leagues")
async def get_leagues(
    tournamentId: Optional[int] = None,
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    try:
        return fetch("/leagues", {"tournamentId": tournamentId, "limit": limit, "offset": offset})
    except Exception as e:
        raise HTTPException(502, detail=f"Football API error: {e}")


@router.get("/rankings")
async def get_rankings(
    leagueId: Optional[int] = None,
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    try:
        return fetch("/rankings", {"leagueId": leagueId, "limit": limit, "offset": offset})
    except Exception as e:
        raise HTTPException(502, detail=f"Football API error: {e}")


@router.get("/trainings")
async def get_trainings(
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    try:
        return fetch("/trainings", {"limit": limit, "offset": offset})
    except Exception as e:
        raise HTTPException(502, detail=f"Football API error: {e}")


@router.get("/attendance")
async def get_attendance(
    matchId: Optional[int] = None,
    playerId: Optional[int] = None,
    teamId: Optional[int] = None,
    scope: Optional[str] = None,
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    try:
        return fetch("/attendance", {"matchId": matchId, "playerId": playerId, "teamId": teamId, "scope": scope, "limit": limit, "offset": offset})
    except Exception as e:
        raise HTTPException(502, detail=f"Football API error: {e}")


@router.get("/notifications")
async def get_notifications(
    userId: Optional[int] = None,
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    try:
        return fetch("/notifications", {"userId": userId, "limit": limit, "offset": offset})
    except Exception as e:
        raise HTTPException(502, detail=f"Football API error: {e}")
