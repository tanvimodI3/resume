"""
Migration script to update the database schema
Run this once to fix the candidate_details table structure
"""
from sqlalchemy import text
import db
from services import models

# Drop the old candidate_details table if it exists
with db.engine.connect() as connection:
    connection.execute(text("DROP TABLE IF EXISTS candidate_details CASCADE;"))
    connection.commit()
    print("✓ Dropped old candidate_details table")

# Create all tables with the new schema from ORM models
models.Base.metadata.create_all(bind=db.engine)
print("✓ Created tables with new schema")
print("Migration complete!")
