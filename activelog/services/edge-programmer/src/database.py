"""
Database models for Edge Device Programmer Service
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, JSON, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, relationship
import asyncio

Base = declarative_base()


# Enums
class DeviceType(str, Enum):
    ARDUINO_UNO = "arduino_uno"
    ARDUINO_NANO = "arduino_nano"
    ARDUINO_MEGA = "arduino_mega"
    ESP32 = "esp32"
    ESP8266 = "esp8266"
    RASPBERRY_PI_PICO = "raspberry_pi_pico"
    TEENSY = "teensy"


class PinType(str, Enum):
    DIGITAL = "digital"
    ANALOG = "analog"
    PWM = "pwm"
    I2C_SDA = "i2c_sda"
    I2C_SCL = "i2c_scl"
    SPI_MOSI = "spi_mosi"
    SPI_MISO = "spi_miso"
    SPI_SCK = "spi_sck"
    UART_TX = "uart_tx"
    UART_RX = "uart_rx"
    POWER = "power"
    GROUND = "ground"


class SensorType(str, Enum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    PRESSURE = "pressure"
    LIGHT = "light"
    MOTION = "motion"
    DISTANCE = "distance"
    ACCELEROMETER = "accelerometer"
    GYROSCOPE = "gyroscope"
    MAGNETOMETER = "magnetometer"
    GPS = "gps"
    CAMERA = "camera"
    MICROPHONE = "microphone"
    SOIL_MOISTURE = "soil_moisture"
    PH_SENSOR = "ph_sensor"
    GAS_SENSOR = "gas_sensor"
    FLAME_SENSOR = "flame_sensor"


class CodeGenerationStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPILING = "compiling"
    UPLOADING = "uploading"


class DeviceStatus(str, Enum):
    OFFLINE = "offline"
    ONLINE = "online"
    UPDATING = "updating"
    ERROR = "error"
    PROVISIONING = "provisioning"
    DEBUGGING = "debugging"


class OTAUpdateStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLBACK = "rollback"


# Core Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    activelog_account_id = Column(String, nullable=True)
    api_key = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    devices = relationship("Device", back_populates="owner")
    code_generations = relationship("CodeGeneration", back_populates="user")
    device_templates = relationship("DeviceTemplate", back_populates="creator")


class Device(Base):
    __tablename__ = "devices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    device_type = Column(SQLEnum(DeviceType), nullable=False)
    mac_address = Column(String, unique=True, nullable=True)
    ip_address = Column(String, nullable=True)
    firmware_version = Column(String, nullable=True)
    status = Column(SQLEnum(DeviceStatus), default=DeviceStatus.OFFLINE)
    last_seen = Column(DateTime, nullable=True)
    location = Column(String, nullable=True)
    metadata = Column(JSON, nullable=True)
    power_consumption = Column(Float, nullable=True)
    battery_level = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="devices")
    pin_configurations = relationship("PinConfiguration", back_populates="device")
    sensor_readings = relationship("SensorReading", back_populates="device")
    ota_updates = relationship("OTAUpdate", back_populates="device")
    debug_sessions = relationship("DebugSession", back_populates="device")


class CodeGeneration(Base):
    __tablename__ = "code_generations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    natural_language_input = Column(Text, nullable=False)
    generated_code = Column(Text, nullable=True)
    device_type = Column(SQLEnum(DeviceType), nullable=False)
    status = Column(SQLEnum(CodeGenerationStatus), default=CodeGenerationStatus.PENDING)
    compilation_output = Column(Text, nullable=True)
    upload_output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    processing_time = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("device_templates.id"), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="code_generations")
    device = relationship("Device")
    template = relationship("DeviceTemplate")


class DeviceTemplate(Base):
    __tablename__ = "device_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    device_type = Column(SQLEnum(DeviceType), nullable=False)
    code_template = Column(Text, nullable=False)
    pin_configuration = Column(JSON, nullable=True)
    required_libraries = Column(JSON, nullable=True)
    category = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)
    usage_count = Column(Integer, default=0)
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    creator = relationship("User", back_populates="device_templates")


class PinConfiguration(Base):
    __tablename__ = "pin_configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pin_number = Column(Integer, nullable=False)
    pin_type = Column(SQLEnum(PinType), nullable=False)
    function = Column(String, nullable=True)
    sensor_type = Column(SQLEnum(SensorType), nullable=True)
    is_active = Column(Boolean, default=True)
    configuration = Column(JSON, nullable=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    
    # Relationships
    device = relationship("Device", back_populates="pin_configurations")


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sensor_type = Column(SQLEnum(SensorType), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=True)
    pin_number = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, nullable=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    
    # Relationships
    device = relationship("Device", back_populates="sensor_readings")


class OTAUpdate(Base):
    __tablename__ = "ota_updates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firmware_version = Column(String, nullable=False)
    firmware_url = Column(String, nullable=False)
    checksum = Column(String, nullable=False)
    status = Column(SQLEnum(OTAUpdateStatus), default=OTAUpdateStatus.PENDING)
    progress = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    
    # Relationships
    device = relationship("Device", back_populates="ota_updates")


class DebugSession(Base):
    __tablename__ = "debug_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    
    # Relationships
    device = relationship("Device", back_populates="debug_sessions")
    debug_messages = relationship("DebugMessage", back_populates="session")


class DebugMessage(Base):
    __tablename__ = "debug_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message = Column(Text, nullable=False)
    level = Column(String, nullable=False)  # INFO, WARNING, ERROR, DEBUG
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String, nullable=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("debug_sessions.id"), nullable=False)
    
    # Relationships
    session = relationship("DebugSession", back_populates="debug_messages")


class PowerProfile(Base):
    __tablename__ = "power_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    cpu_frequency = Column(Integer, nullable=True)
    wifi_mode = Column(String, nullable=True)
    sleep_mode = Column(String, nullable=True)
    sensor_sampling_rate = Column(Float, nullable=True)
    estimated_power_consumption = Column(Float, nullable=True)
    estimated_battery_life = Column(Float, nullable=True)
    configuration = Column(JSON, nullable=False)
    device_type = Column(SQLEnum(DeviceType), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class SerialConnection(Base):
    __tablename__ = "serial_connections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    port = Column(String, nullable=False)
    baud_rate = Column(Integer, default=115200)
    is_connected = Column(Boolean, default=False)
    last_activity = Column(DateTime, nullable=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=True)
    
    # Relationships
    device = relationship("Device")


class FleetGroup(Base):
    __tablename__ = "fleet_groups"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    device_ids = Column(JSON, nullable=False)
    configuration = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    owner = relationship("User")


# Database configuration
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/edge_programmer"
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()