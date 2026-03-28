from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from . import database
from .database import SessionLocal, engine, Building, Pixel

database.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Unity Backend")

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

class RecommendRequest(BaseModel):
    buildingId: str

@app.get("/buildings/{building_id}", response_model=BuildingResponse)
def get_or_create_building(building_id: str, db: Session = Depends(get_db)):
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        building = Building(id=building_id, recommend_count=0, summary="New building detected")
        db.add(building)
        db.commit()
        db.refresh(building)
    
    return BuildingResponse(
        buildingId=building.id,
        recommendCount=building.recommend_count,
        summary=building.summary
    )

@app.get("/buildings/{building_id}/pixels", response_model=List[PixelBase])
def get_building_pixels(building_id: str, db: Session = Depends(get_db)):
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        return []
    
    pixels = db.query(Pixel).filter(Pixel.building_id == building_id).all()
    return [
        PixelBase(
            buildingId=p.building_id,
            face=p.face,
            x=p.x,
            y=p.y,
            color=p.color
        ) for p in pixels
    ]

@app.post("/pixels")
def create_or_update_pixel(pixel: PixelBase, db: Session = Depends(get_db)):
    building = db.query(Building).filter(Building.id == pixel.buildingId).first()
    if not building:
        building = Building(id=pixel.buildingId, recommend_count=0, summary="New building detected")
        db.add(building)
        db.commit()

    existing_pixel = db.query(Pixel).filter(
        Pixel.building_id == pixel.buildingId,
        Pixel.face == pixel.face,
        Pixel.x == pixel.x,
        Pixel.y == pixel.y
    ).first()

    if existing_pixel:
        existing_pixel.color = pixel.color
    else:
        new_pixel = Pixel(
            building_id=pixel.buildingId,
            face=pixel.face,
            x=pixel.x,
            y=pixel.y,
            color=pixel.color
        )
        db.add(new_pixel)
    
    db.commit()
    return {"status": "success"}

@app.delete("/pixels")
def delete_pixel(buildingId: str, face: int, x: int, y: int, db: Session = Depends(get_db)):
    pixel = db.query(Pixel).filter(
        Pixel.building_id == buildingId,
        Pixel.face == face,
        Pixel.x == x,
        Pixel.y == y
    ).first()
    if pixel:
        db.delete(pixel)
        db.commit()
    return {"status": "success"}

@app.post("/buildings/recommend")
def recommend_building(req: RecommendRequest, db: Session = Depends(get_db)):
    building = db.query(Building).filter(Building.id == req.buildingId).first()
    if not building:
        building = Building(id=req.buildingId, recommend_count=0, summary="New building detected")
        db.add(building)
        db.commit()
    
    building.recommend_count += 1
    db.commit()
    return {"buildingId": building.id, "recommendCount": building.recommend_count}