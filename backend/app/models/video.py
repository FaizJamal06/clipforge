from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from app.database import Base
import json

class ProcessedVideo(Base):
    """
    Cache table to store the final output of the LangGraph AI processing.
    Instead of re-running expensive LLM operations for the same youtube_id,
    we can instantly serve the cached results.
    """
    __tablename__ = "processed_videos"

    video_id = Column(String(50), primary_key=True, index=True)
    youtube_url = Column(String(255), nullable=False)
    
    # Store the entire ProcessResponse output directly as a JSON string
    response_payload = Column(String, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def set_payload(self, payload_dict: dict):
        self.response_payload = json.dumps(payload_dict)
        
    def get_payload(self) -> dict:
        return json.loads(self.response_payload)
