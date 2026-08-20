import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import CheckIn
from app.schemas import (
    ReflectionChatRequest,
    ReflectionFinishResponse,
    ReflectionResponse,
)
from app.services.llm import stream_chat
from app.services.reflection import (
    get_conversation_messages,
    get_or_create_system_message,
    messages_to_ollama_format,
    save_message,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reflections", tags=["reflections"])


@router.get("/{checkin_id}", response_model=ReflectionResponse)
def get_reflection(checkin_id: int, db: Session = Depends(get_db)):
    check_in = db.query(CheckIn).filter(CheckIn.id == checkin_id).first()
    if not check_in:
        raise HTTPException(status_code=404, detail="Check-in not found")

    messages = get_conversation_messages(db, checkin_id)
    visible = [m for m in messages if m.role != "system"]

    return ReflectionResponse(
        messages=visible,
        finished=check_in.reflection_finished,
    )


@router.post("/{checkin_id}/chat")
def chat(checkin_id: int, body: ReflectionChatRequest, db: Session = Depends(get_db)):
    check_in = db.query(CheckIn).filter(CheckIn.id == checkin_id).first()
    if not check_in:
        raise HTTPException(status_code=404, detail="Check-in not found")
    if check_in.status != "completed":
        raise HTTPException(
            status_code=409, detail="Check-in must be completed before reflecting"
        )
    if check_in.reflection_finished:
        raise HTTPException(status_code=409, detail="Reflection already finished")

    get_or_create_system_message(db, check_in)

    if body.message is not None:
        save_message(db, checkin_id, "user", body.message)

    all_messages = get_conversation_messages(db, checkin_id)
    ollama_messages = messages_to_ollama_format(all_messages)

    def generate():
        gen_db = SessionLocal()
        full_response = ""
        try:
            for token in stream_chat(ollama_messages):
                full_response += token
                yield f"event: token\ndata: {json.dumps({'content': token})}\n\n"

            msg = save_message(gen_db, checkin_id, "assistant", full_response)
            yield f"event: done\ndata: {json.dumps({'message_id': msg.id})}\n\n"
        except GeneratorExit:
            logger.info("Client disconnected during reflection for check-in %d", checkin_id)
        except Exception:
            logger.exception("Reflection chat error for check-in %d", checkin_id)
            yield f"event: error\ndata: {json.dumps({'detail': 'Reflection unavailable — please try again.'})}\n\n"
        finally:
            gen_db.close()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/{checkin_id}/finish", response_model=ReflectionFinishResponse)
def finish(checkin_id: int, db: Session = Depends(get_db)):
    check_in = db.query(CheckIn).filter(CheckIn.id == checkin_id).first()
    if not check_in:
        raise HTTPException(status_code=404, detail="Check-in not found")

    messages = get_conversation_messages(db, checkin_id)
    visible = [m for m in messages if m.role != "system"]
    if not visible:
        raise HTTPException(status_code=409, detail="No reflection messages to save")

    from app.services.journal import write_reflection_entry

    check_in.reflection_finished = True
    check_in.reflection_journal_written = write_reflection_entry(check_in, visible)
    db.commit()

    return ReflectionFinishResponse(
        journal_written=check_in.reflection_journal_written
    )
