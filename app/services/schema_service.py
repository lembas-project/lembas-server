"""Service for the handler schema registry."""

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import HandlerSchema
from app.database.models import Study
from app.database.models import StudyHandlerSchema


async def upsert_schemas(
    db: AsyncSession,
    study: Study,
    schemas: list[dict[str, Any]],
) -> None:
    """Insert handler schemas that don't exist yet and link them to a study.

    Each schema dict must have:
      - ``fingerprint``: 16–64 char hex string
      - ``name``: handler class name
      - the rest: full JSON Schema blob
    """
    for schema_dict in schemas:
        fingerprint = schema_dict["fingerprint"]
        name = schema_dict["name"]
        # The schema blob is everything except our registry metadata keys
        blob = {k: v for k, v in schema_dict.items() if k not in ("fingerprint", "name")}

        # Upsert the schema itself (ignore if fingerprint already exists)
        existing = await db.get(HandlerSchema, fingerprint)
        if existing is None:
            db.add(
                HandlerSchema(
                    fingerprint=fingerprint,
                    name=name,
                    schema_json=json.dumps(blob),
                )
            )

        # Link to study if not already linked
        link = await db.get(StudyHandlerSchema, (study.id, fingerprint))
        if link is None:
            db.add(StudyHandlerSchema(study_id=study.id, fingerprint=fingerprint))

    await db.commit()


async def get_all_schemas(db: AsyncSession) -> list[dict[str, Any]]:
    """Return all schemas with usage information (which studies use each)."""
    result = await db.execute(
        select(HandlerSchema)
        .order_by(HandlerSchema.name, HandlerSchema.created_at)
        .options(selectinload(HandlerSchema.studies))
    )
    schemas = result.scalars().all()

    return [
        {
            "fingerprint": s.fingerprint,
            "name": s.name,
            "schema": json.loads(s.schema_json),
            "created_at": s.created_at,
            "used_by": [{"study_id": study.id, "study_name": study.name} for study in s.studies],
        }
        for s in schemas
    ]


async def get_schema(db: AsyncSession, fingerprint: str) -> dict[str, Any] | None:
    """Return a single schema by fingerprint, or None if not found."""
    schema = await db.get(HandlerSchema, fingerprint)
    if schema is None:
        return None
    return {
        "fingerprint": schema.fingerprint,
        "name": schema.name,
        "schema": json.loads(schema.schema_json),
        "created_at": schema.created_at,
    }
