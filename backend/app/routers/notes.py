from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.models import LeadNote, LeadActivity
from app.schemas.schemas import LeadNoteCreate, LeadNoteOut

router = APIRouter(prefix="/api/leads", tags=["Notes"])


@router.get("/{lead_id}/notes", response_model=List[LeadNoteOut])
async def list_notes(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Get all notes for a lead."""
    result = await db.execute(
        select(LeadNote)
        .where(LeadNote.lead_id == lead_id)
        .order_by(LeadNote.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{lead_id}/notes", response_model=LeadNoteOut)
async def add_note(
    lead_id: int,
    note: LeadNoteCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add a note to a lead."""
    db_note = LeadNote(lead_id=lead_id, **note.model_dump())
    db.add(db_note)

    # Also track note-adding as an activity
    activity = LeadActivity(
        lead_id=lead_id,
        activity_type="Note Added",
        description=f"Note added: {note.note_text[:80]}..."
    )
    db.add(activity)

    await db.commit()
    await db.refresh(db_note)
    return db_note


@router.delete("/{lead_id}/notes/{note_id}")
async def delete_note(
    lead_id: int, note_id: int, db: AsyncSession = Depends(get_db)
):
    """Delete a note."""
    result = await db.execute(
        select(LeadNote).where(LeadNote.id == note_id, LeadNote.lead_id == lead_id)
    )
    db_note = result.scalar_one_or_none()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    await db.delete(db_note)
    await db.commit()
    return {"detail": "Note deleted"}
