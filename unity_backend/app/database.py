from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

SQLALCHEMY_DATABASE_URL = "sqlite:///./unity_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Building(Base):
    __tablename__ = "buildings"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=True)
    recommend_count = Column(Integer, default=0)
    summary = Column(String, default="")

    pixels = relationship("Pixel", back_populates="building")

class Pixel(Base):
    __tablename__ = "pixels"
    __table_args__ = (UniqueConstraint('building_id', 'face', 'x', 'y', name='_building_face_x_y_uc'),)

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(String, ForeignKey("buildings.id"))
    face = Column(Integer)
    x = Column(Integer)
    y = Column(Integer)
    color = Column(String)

    building = relationship("Building", back_populates="pixels")
