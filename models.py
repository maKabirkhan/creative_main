from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column, String, Date, Boolean, Integer, Float, DateTime,
    ForeignKey, Enum, func, ARRAY, Text
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
import enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text


Base = declarative_base()

class TimestampMixin:
    """Mixin for timestamp fields"""
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SubscriptionTier(enum.Enm):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    AGENCY = "agency"
    ENTERPRISE = "enterprise"


class AssetType(enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"


class AuthProvider(enum.Enum):
    LOCAL = "local"
    GOOGLE = "google"


class TestMode(enum.Enum):
    A_B_TEST = "A/B Test"
    MULTIVARIATE = "Multivariate"
    OTHER = "Other"

class TestStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        nullable=False
    )
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    avatar = Column(String)
    role = Column(String)
    company = Column(String)
    password_reset_token = Column(String)
    password_reset_expires = Column(DateTime(timezone=True))
    pending_password_hash = Column(String)
    two_factor = Column(Boolean, default=False, nullable=False)
    auth_provider = Column(Enum(AuthProvider), default=AuthProvider.LOCAL, nullable=False)
    google_id = Column(String)
    projects_count = Column(Integer, default=0, nullable=False)
    pretests_count = Column(Integer, default=0, nullable=False)
    
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    personas = relationship("Persona", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")

class Persona(Base, TimestampMixin):
    __tablename__ = "personas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    audience_type = Column(String)
    geography = Column(String)
    age_min = Column(Integer)
    age_max = Column(Integer)
    income_min = Column(Float)
    income_max = Column(Float)
    gender = Column(String)
    purchase_frequency = Column(String)
    interests = Column(ARRAY(String))
    life_stage = Column(String)
    category_involvement = Column(String)
    decision_making_style = Column(String)
    min_reach = Column(Integer)
    max_reach = Column(Integer)
    efficiency = Column(String)
    platforms = Column(String)
    peak_activity = Column(String)
    engagement = Column(String)

    clarity = Column(Float)
    relevance = Column(Float)
    distinctiveness = Column(Float)
    brand_fit = Column(Float)
    emotion = Column(Float)
    cta = Column(Float)
    inclusivity = Column(Float)

    user = relationship("User", back_populates="personas")
    test_sessions = relationship("TestSession", back_populates="persona", cascade="all, delete-orphan")
    persona_profile = relationship(
        "PersonaProfile",
        back_populates="persona",
        uselist=False,
        cascade="all, delete-orphan"
    )


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    name = Column(String, nullable=False)
    brand = Column(String)
    product = Column(String)
    product_service_type = Column(String)
    category = Column(String)
    market_maturity = Column(String)
    campaign_objective = Column(String)
    value_propositions = Column(String)
    media_channels = Column(ARRAY(String))
    kpis = Column(String)
    kpi_target = Column(String)

    user = relationship("User", back_populates="projects")
    creative_assets = relationship("CreativeAsset", back_populates="project", cascade="all, delete-orphan")
    test_sessions = relationship("TestSession", back_populates="project", cascade="all, delete-orphan")


class CreativeAsset(Base):
    __tablename__ = "creative_assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    type = Column(Enum(AssetType), nullable=False)
    name = Column(String, nullable=False)
    file_url = Column(String)
    ad_copy = Column(Text)
    voice_script = Column(Text)
    meta_data = Column(JSON)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="creative_assets")
    asset_metadata = relationship("AssetMetadata", back_populates="asset", cascade="all, delete-orphan")
    test_sessions_a = relationship("TestSession", foreign_keys="TestSession.creative_a_id", back_populates="creative_a")
    test_sessions_b = relationship("TestSession", foreign_keys="TestSession.creative_b_id", back_populates="creative_b")

class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tier = Column(String, nullable=False)  
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    auto_renew = Column(Boolean, default=True)
    stripe_customer_id = Column(String)
    stripe_subscription_id = Column(String) 
    status = Column(String, default="active") 

    user = relationship("User", back_populates="subscriptions")


class PersonaProfile(Base):
    __tablename__ = "persona_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    persona_id = Column(Integer, ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    demographics = Column(JSON)
    psychographics = Column(JSON)
    goals_barriers = Column(JSON)
    media_habits = Column(JSON)

    persona = relationship("Persona", back_populates="persona_profile")


class TestSession(Base):
    __tablename__ = "test_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    persona_id = Column(Integer, ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    creative_a_id = Column(Integer, ForeignKey("creative_assets.id", ondelete="CASCADE"), nullable=False)
    creative_b_id = Column(Integer, ForeignKey("creative_assets.id", ondelete="CASCADE"))
    mode = Column(Enum(TestMode), nullable=False)
    status = Column(Enum(TestStatus), default=TestStatus.PENDING)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    project = relationship("Project", back_populates="test_sessions")
    persona = relationship("Persona", back_populates="test_sessions")
    creative_a = relationship("CreativeAsset", foreign_keys=[creative_a_id], back_populates="test_sessions_a")
    creative_b = relationship("CreativeAsset", foreign_keys=[creative_b_id], back_populates="test_sessions_b")
    synthetic_results = relationship(
        "SyntheticResults",
        back_populates="test_session",
        uselist=False,
        cascade="all, delete-orphan"
    )


class SyntheticResults(Base):
    __tablename__ = "synthetic_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_session_id = Column(Integer, ForeignKey("test_sessions.id", ondelete="CASCADE"), nullable=False)
    general_audience_responses = Column(JSON)
    target_persona_responses = Column(JSON)
    creative_director_responses = Column(JSON)
    ces_scores = Column(JSON)
    statistical_analysis = Column(JSON)
    winner = Column(String)
    confidence_score = Column(Float)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    test_session = relationship("TestSession", back_populates="synthetic_results")


class PersonaLibrary(Base, TimestampMixin):
    __tablename__ = "persona_library"

    id = Column(Integer, primary_key=True, autoincrement=True)
    audience_name = Column(String(255), nullable=False)
    audience_type = Column(String(100))
    geography = Column(String(255))
    age_min = Column(Integer)
    age_max = Column(Integer)
    income_min = Column(Float)
    income_max = Column(Float)
    gender = Column(String(50))
    interests = Column(ARRAY(String))
    purchase_frequency = Column(String)
    life_stage = Column(String(100))
    category_involvement = Column(String(100))
    decision_making_style = Column(String(100))

    def __repr__(self):
        return f"<PersonaLibrary(id={self.id}, audience_name={self.audience_name})>"



class AssetMetadata(Base):
    __tablename__ = "asset_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("creative_assets.id", ondelete="CASCADE"), nullable=False)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    asset = relationship("CreativeAsset", back_populates="asset_metadata")
