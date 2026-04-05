"""API models for thought-related endpoints."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator, root_validator

from src.domain.entities.semantic_entry import SemanticEntry
from src.domain.entities.thought import GeoLocation, Thought, ThoughtMetadata, WeatherData


class GeoLocationRequest(BaseModel):
    """Request model for geographic location."""

    latitude: float = Field(
        ..., 
        ge=-90, 
        le=90, 
        description="Latitude coordinate (-90 to 90 degrees)",
        example=40.7128
    )
    longitude: float = Field(
        ..., 
        ge=-180, 
        le=180, 
        description="Longitude coordinate (-180 to 180 degrees)",
        example=-74.0060
    )
    name: Optional[str] = Field(
        None, 
        max_length=200,
        description="Optional human-readable location name",
        example="Downtown Coffee Shop"
    )

    @validator('name')
    def validate_name(cls, v):
        """Validate location name."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class WeatherDataRequest(BaseModel):
    """Request model for weather information."""

    temperature: Optional[float] = Field(
        None, 
        ge=-50, 
        le=60, 
        description="Temperature in Celsius (-50 to 60 degrees)",
        example=22.5
    )
    condition: Optional[str] = Field(
        None, 
        max_length=50,
        description="Weather condition description",
        example="sunny"
    )
    humidity: Optional[float] = Field(
        None, 
        ge=0, 
        le=100, 
        description="Humidity percentage (0-100%)",
        example=65.0
    )

    @validator('condition')
    def validate_condition(cls, v):
        """Validate weather condition."""
        if v is not None:
            v = v.strip().lower()
            if not v:
                return None
            # List of valid weather conditions
            valid_conditions = {
                'sunny', 'cloudy', 'partly cloudy', 'overcast', 'rainy', 'drizzle',
                'thunderstorm', 'snowy', 'foggy', 'windy', 'clear', 'hazy'
            }
            if v not in valid_conditions:
                # Allow any condition but normalize it
                pass
        return v


class ThoughtMetadataRequest(BaseModel):
    """Request model for thought metadata."""

    location: Optional[GeoLocationRequest] = None
    weather: Optional[WeatherDataRequest] = None
    mood: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    custom: Dict[str, str] = Field(default_factory=dict)

    def to_domain(self) -> ThoughtMetadata:
        """Convert to domain ThoughtMetadata.

        Returns:
            Domain ThoughtMetadata object
        """
        location = None
        if self.location:
            location = GeoLocation(
                latitude=self.location.latitude,
                longitude=self.location.longitude,
                name=self.location.name,
            )

        weather = None
        if self.weather:
            weather = WeatherData(
                temperature=self.weather.temperature,
                condition=self.weather.condition,
                humidity=self.weather.humidity,
            )

        return ThoughtMetadata(
            location=location,
            weather=weather,
            mood=self.mood,
            tags=self.tags,
            custom=self.custom,
        )


class CreateThoughtRequest(BaseModel):
    """Request model for creating a thought."""

    content: str = Field(
        ..., 
        min_length=1, 
        max_length=10000,
        description="The thought content (1-10,000 characters)",
        example="Had a great meeting with Sarah at the coffee shop downtown. We discussed the new project proposal and I'm feeling optimistic about the collaboration."
    )
    metadata: Optional[ThoughtMetadataRequest] = Field(
        None,
        description="Optional metadata including location, weather, mood, and tags"
    )
    timestamp: Optional[datetime] = Field(
        None,
        description="Optional timestamp for the thought (defaults to current time if not provided)"
    )

    @validator('content')
    def validate_content(cls, v):
        """Validate thought content."""
        if not v.strip():
            raise ValueError('Content cannot be empty or only whitespace')
        
        # Check for potentially harmful content
        if len(v.strip()) < 3:
            raise ValueError('Content must be at least 3 characters long')
            
        return v.strip()

    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Validate timestamp is not in the future."""
        if v and v > datetime.now():
            raise ValueError('Timestamp cannot be in the future')
        return v

    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "content": "Had a great meeting with Sarah at the coffee shop downtown. We discussed the new project proposal and I'm feeling optimistic about the collaboration.",
                "metadata": {
                    "location": {
                        "latitude": 40.7128,
                        "longitude": -74.0060,
                        "name": "Downtown Coffee Shop"
                    },
                    "weather": {
                        "temperature": 22.5,
                        "condition": "sunny",
                        "humidity": 65.0
                    },
                    "mood": "optimistic",
                    "tags": ["work", "meeting", "collaboration"],
                    "custom": {
                        "project": "new-proposal",
                        "priority": "high"
                    }
                },
                "timestamp": "2024-01-15T14:30:00Z"
            }
        }


class UpdateThoughtRequest(BaseModel):
    """Request model for updating a thought."""

    content: Optional[str] = Field(None, min_length=1, description="The updated thought content")
    metadata: Optional[ThoughtMetadataRequest] = None


class GeoLocationResponse(BaseModel):
    """Response model for geographic location."""

    latitude: float
    longitude: float
    name: Optional[str] = None

    @classmethod
    def from_domain(cls, location: GeoLocation) -> "GeoLocationResponse":
        """Create from domain GeoLocation.

        Args:
            location: Domain GeoLocation object

        Returns:
            GeoLocationResponse object
        """
        return cls(
            latitude=location.latitude,
            longitude=location.longitude,
            name=location.name,
        )


class WeatherDataResponse(BaseModel):
    """Response model for weather information."""

    temperature: Optional[float] = None
    condition: Optional[str] = None
    humidity: Optional[float] = None

    @classmethod
    def from_domain(cls, weather: WeatherData) -> "WeatherDataResponse":
        """Create from domain WeatherData.

        Args:
            weather: Domain WeatherData object

        Returns:
            WeatherDataResponse object
        """
        return cls(
            temperature=weather.temperature,
            condition=weather.condition,
            humidity=weather.humidity,
        )


class ThoughtMetadataResponse(BaseModel):
    """Response model for thought metadata."""

    location: Optional[GeoLocationResponse] = None
    weather: Optional[WeatherDataResponse] = None
    mood: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    custom: Dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, metadata: ThoughtMetadata) -> "ThoughtMetadataResponse":
        """Create from domain ThoughtMetadata.

        Args:
            metadata: Domain ThoughtMetadata object

        Returns:
            ThoughtMetadataResponse object
        """
        location = None
        if metadata.location:
            location = GeoLocationResponse.from_domain(metadata.location)

        weather = None
        if metadata.weather:
            weather = WeatherDataResponse.from_domain(metadata.weather)

        return cls(
            location=location,
            weather=weather,
            mood=metadata.mood,
            tags=metadata.tags,
            custom=metadata.custom,
        )


class SemanticEntryResponse(BaseModel):
    """Response model for semantic entries."""

    id: UUID
    entity_type: str
    entity_value: str
    confidence: float
    context: str
    extracted_at: datetime

    @classmethod
    def from_domain(cls, entry: SemanticEntry) -> "SemanticEntryResponse":
        """Create from domain SemanticEntry.

        Args:
            entry: Domain SemanticEntry object

        Returns:
            SemanticEntryResponse object
        """
        return cls(
            id=entry.id,
            entity_type=entry.entity_type.value,
            entity_value=entry.entity_value,
            confidence=entry.confidence,
            context=entry.context,
            extracted_at=entry.extracted_at,
        )


class ThoughtResponse(BaseModel):
    """Response model for thoughts."""

    id: UUID
    content: str
    timestamp: datetime
    metadata: ThoughtMetadataResponse
    semantic_entries: List[SemanticEntryResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, thought: Thought) -> "ThoughtResponse":
        """Create from domain Thought.

        Args:
            thought: Domain Thought object

        Returns:
            ThoughtResponse object
        """
        return cls(
            id=thought.id,
            content=thought.content,
            timestamp=thought.timestamp,
            metadata=ThoughtMetadataResponse.from_domain(thought.metadata),
            semantic_entries=[
                SemanticEntryResponse.from_domain(entry)
                for entry in thought.semantic_entries
            ],
            created_at=thought.created_at,
            updated_at=thought.updated_at,
        )


class ThoughtListResponse(BaseModel):
    """Response model for paginated thought lists."""

    thoughts: List[ThoughtResponse]
    total: int
    skip: int
    limit: int

    @classmethod
    def from_domain_list(
        cls, thoughts: List[Thought], total: int, skip: int, limit: int
    ) -> "ThoughtListResponse":
        """Create from list of domain Thoughts.

        Args:
            thoughts: List of domain Thought objects
            total: Total number of thoughts available
            skip: Number of thoughts skipped
            limit: Maximum number of thoughts returned

        Returns:
            ThoughtListResponse object
        """
        return cls(
            thoughts=[ThoughtResponse.from_domain(thought) for thought in thoughts],
            total=total,
            skip=skip,
            limit=limit,
        )


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)