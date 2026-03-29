"""Import endpoints — NetBox, Nautobot, NetGraphy."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from snep.api.deps import DBSession

router = APIRouter()


class NetBoxImportRequest(BaseModel):
    url: str
    token: str
    site_filter: str | None = None
    role_filter: str | None = None
    tag_filter: str | None = None


class NetGraphyImportRequest(BaseModel):
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "netgraphy"
    hostname_filter: str | None = None


@router.post("/netbox")
async def import_from_netbox(body: NetBoxImportRequest, db: DBSession):
    """Import devices, interfaces, and cables from NetBox via GraphQL."""
    from snep.importers.netbox import import_netbox
    try:
        result = await import_netbox(db, body.url, body.token, body.site_filter, body.role_filter, body.tag_filter)
        return result
    except Exception as e:
        raise HTTPException(500, f"Import failed: {str(e)}")


@router.post("/nautobot")
async def import_from_nautobot(body: NetBoxImportRequest, db: DBSession):
    """Import devices, interfaces, and cables from Nautobot via GraphQL."""
    from snep.importers.nautobot import import_nautobot
    try:
        result = await import_nautobot(db, body.url, body.token, body.site_filter, body.role_filter, body.tag_filter)
        return result
    except Exception as e:
        raise HTTPException(500, f"Import failed: {str(e)}")


@router.post("/netgraphy")
async def import_from_netgraphy(body: NetGraphyImportRequest, db: DBSession):
    """Import devices, interfaces, and cables from NetGraphy via Neo4j."""
    from snep.importers.netgraphy import import_netgraphy
    try:
        result = await import_netgraphy(
            db, body.neo4j_uri, body.neo4j_user, body.neo4j_password, body.hostname_filter
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"Import failed: {str(e)}")
