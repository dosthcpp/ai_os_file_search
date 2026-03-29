import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import anthropic

from . import database
from .database import SessionLocal, engine, Building, Pixel

database.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Unity AR Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_anthropic_client = None

def get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class BuildingResponse(BaseModel):
    buildingId: str
    recommendCount: int
    summary: str


class PixelBase(BaseModel):
    buildingId: str
    face: int
    x: int
    y: int
    color: str


class PixelBatch(BaseModel):
    pixels: List[PixelBase]


class RecommendRequest(BaseModel):
    buildingId: str


class BuildingRegisterRequest(BaseModel):
    name: Optional[str] = None


# Thresholds at which AI regenerates the summary
SUMMARY_THRESHOLDS = {3, 5, 10, 20, 50}


def _generate_ai_summary(building: Building) -> str:
    """Generate an AI-powered summary for a building using Claude."""
    client = get_anthropic_client()
    if not client:
        return f"A beloved landmark with {building.recommend_count} recommendations."

    name_str = building.name if building.name else f"Building #{building.id[:8]}"
    prompt = (
        f"You are writing a short, vivid AR description for a real building that appears "
        f"in an augmented reality city app. The building is called \"{name_str}\" and has "
        f"received {building.recommend_count} community recommendation(s). "
        f"Write a single engaging sentence (max 20 words) that captures the community love "
        f"for this building. Be warm, creative, and concise."
    )

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=64,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip().strip('"')
    except Exception as e:
        return f"A community favourite with {building.recommend_count} recommendation(s)."


@app.get("/buildings/{building_id}", response_model=BuildingResponse)
def get_or_create_building(building_id: str, db: Session = Depends(get_db)):
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        building = Building(id=building_id, recommend_count=0, summary="")
        db.add(building)
        db.commit()
        db.refresh(building)

    return BuildingResponse(
        buildingId=building.id,
        recommendCount=building.recommend_count,
        summary=building.summary or "",
    )


@app.put("/buildings/{building_id}")
def register_building(
    building_id: str,
    req: BuildingRegisterRequest,
    db: Session = Depends(get_db),
):
    """Register or update a building's name (called by Unity on init)."""
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        building = Building(id=building_id, recommend_count=0, summary="")
        db.add(building)

    if req.name:
        building.name = req.name

    db.commit()
    return {"status": "ok", "buildingId": building_id, "name": building.name}


@app.get("/buildings/{building_id}/pixels", response_model=List[PixelBase])
def get_building_pixels(building_id: str, updated_after: Optional[float] = None, db: Session = Depends(get_db)):
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        return []

    query = db.query(Pixel).filter(Pixel.building_id == building_id)
    if updated_after:
        dt = datetime.fromtimestamp(updated_after)
        query = query.filter(Pixel.updated_at > dt)

    pixels = query.all()
    return [
        PixelBase(
            buildingId=p.building_id,
            face=p.face,
            x=p.x,
            y=p.y,
            color=p.color,
        )
        for p in pixels
    ]


@app.post("/pixels")
def create_or_update_pixel(pixel: PixelBase, db: Session = Depends(get_db)):
    _upsert_pixel(pixel, db)
    db.commit()
    return {"status": "success"}


@app.post("/pixels/batch")
def batch_update_pixels(batch: PixelBatch, db: Session = Depends(get_db)):
    for pixel in batch.pixels:
        _upsert_pixel(pixel, db)
    db.commit()
    return {"status": "success", "count": len(batch.pixels)}


def _upsert_pixel(pixel: PixelBase, db: Session):
    building = db.query(Building).filter(Building.id == pixel.buildingId).first()
    if not building:
        building = Building(id=pixel.buildingId, recommend_count=0, summary="")
        db.add(building)
        db.flush()

    existing = db.query(Pixel).filter(
        Pixel.building_id == pixel.buildingId,
        Pixel.face == pixel.face,
        Pixel.x == pixel.x,
        Pixel.y == pixel.y,
    ).first()

    if existing:
        existing.color = pixel.color
        existing.updated_at = datetime.now()
    else:
        db.add(Pixel(
            building_id=pixel.buildingId,
            face=pixel.face,
            x=pixel.x,
            y=pixel.y,
            color=pixel.color,
        ))


@app.delete("/pixels")
def delete_pixel(buildingId: str, face: int, x: int, y: int, db: Session = Depends(get_db)):
    pixel = db.query(Pixel).filter(
        Pixel.building_id == buildingId,
        Pixel.face == face,
        Pixel.x == x,
        Pixel.y == y,
    ).first()
    if pixel:
        db.delete(pixel)
        db.commit()
    return {"status": "success"}


@app.post("/buildings/recommend")
def recommend_building(req: RecommendRequest, db: Session = Depends(get_db)):
    building = db.query(Building).filter(Building.id == req.buildingId).first()
    if not building:
        building = Building(id=req.buildingId, recommend_count=0, summary="")
        db.add(building)
        db.commit()

    building.recommend_count += 1

    # Regenerate AI summary at key milestones
    if building.recommend_count in SUMMARY_THRESHOLDS:
        building.summary = _generate_ai_summary(building)

    db.commit()
    return {
        "buildingId": building.id,
        "recommendCount": building.recommend_count,
        "summary": building.summary or "",
    }
