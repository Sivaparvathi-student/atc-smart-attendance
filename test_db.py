from app.database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Database connected successfully!")
        print("Result:", result.fetchone())
except Exception as e:
    print("❌ Database connection FAILED!")
    print("Error type:", type(e).__name__)
    print("Error message:", str(e))