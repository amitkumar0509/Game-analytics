# db_models.py
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

class Category(Base):
    __tablename__ = 'categories'
    category_id = Column(String(50), primary_key=True)
    category_name = Column(String(100), nullable=False)

    competitions = relationship("Competition", back_populates="category")

    def __repr__(self):
        return f"<Category(id='{self.category_id}', name='{self.category_name}')>"

class Competition(Base):
    __tablename__ = 'competitions'
    competition_id = Column(String(50), primary_key=True)
    competition_name = Column(String(100), nullable=False)
    parent_id = Column(String(50), nullable=True) # Could be a self-referencing FK if needed
    type = Column(String(20), nullable=False)
    gender = Column(String(10), nullable=False)
    category_id = Column(String(50), ForeignKey('categories.category_id'))
    level = Column(String(50), nullable=True) # Added based on API response

    category = relationship("Category", back_populates="competitions")

    def __repr__(self):
        return f"<Competition(id='{self.competition_id}', name='{self.competition_name}')>"

class Complex(Base):
    __tablename__ = 'complexes'
    complex_id = Column(String(50), primary_key=True)
    complex_name = Column(String(100), nullable=False)

    venues = relationship("Venue", back_populates="complex")

    def __repr__(self):
        return f"<Complex(id='{self.complex_id}', name='{self.complex_name}')>"

class Venue(Base):
    __tablename__ = 'venues'
    venue_id = Column(String(50), primary_key=True)
    venue_name = Column(String(100), nullable=False)
    city_name = Column(String(100), nullable=False)
    country_name = Column(String(100), nullable=False)
    country_code = Column(String(3), nullable=False)
    timezone = Column(String(100), nullable=False)
    complex_id = Column(String(50), ForeignKey('complexes.complex_id'))

    complex = relationship("Complex", back_populates="venues")

    def __repr__(self):
        return f"<Venue(id='{self.venue_id}', name='{self.venue_name}', city='{self.city_name}')>"

class Competitor(Base):
    __tablename__ = 'competitors'
    competitor_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    country_code = Column(String(3), nullable=False)
    abbreviation = Column(String(10), nullable=False)

    rankings = relationship("CompetitorRanking", back_populates="competitor")

    def __repr__(self):
        return f"<Competitor(id='{self.competitor_id}', name='{self.name}')>"

class CompetitorRanking(Base):
    __tablename__ = 'competitor_rankings'
    rank_id = Column(Integer, primary_key=True, autoincrement=True) # Auto-incremented ID
    rank = Column(Integer, nullable=False)
    movement = Column(Integer, nullable=False)
    points = Column(Integer, nullable=False)
    competitions_played = Column(Integer, nullable=False)
    competitor_id = Column(String(50), ForeignKey('competitors.competitor_id'))

    competitor = relationship("Competitor", back_populates="rankings")

    def __repr__(self):
        return f"<CompetitorRanking(id='{self.rank_id}', competitor_id='{self.competitor_id}', rank='{self.rank}')>"


def create_db_tables(engine):
    """Creates all tables defined in Base."""
    Base.metadata.create_all(engine)
    print("Database tables created or already exist.")