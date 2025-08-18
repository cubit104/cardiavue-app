import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5433  # Updated to your port
    database: str = "cardiavue2"  # Updated to your database name
    username: str = "postgres"  # Updated to your username
    password: str = "password"  # Your password
    
    @property
    def url(self) -> str:
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

@dataclass
class ExtractionConfig:
    input_directory: str = "input_pdfs"
    output_directory: str = "processed_pdfs"
    log_level: str = "INFO"
    max_file_size_mb: int = 50
    
    # Medtronic-specific patterns
    device_models = [
        "Evera MRI XT DR", "Evera MRI XT VR", "Evera XT DR", "Evera XT VR",
        "Protecta XT DR", "Protecta XT VR", "Consulta CRT-P", "Consulta CRT-D"
    ]

# Global configuration instance
db_config = DatabaseConfig()
extraction_config = ExtractionConfig()

# Load from environment variables if available (override defaults)
if os.getenv("DB_HOST"):
    db_config.host = os.getenv("DB_HOST")
if os.getenv("DB_PORT"):
    db_config.port = int(os.getenv("DB_PORT"))
if os.getenv("DB_NAME"):
    db_config.database = os.getenv("DB_NAME")
if os.getenv("DB_USER"):
    db_config.username = os.getenv("DB_USER")
if os.getenv("DB_PASSWORD"):
    db_config.password = os.getenv("DB_PASSWORD")

# Print config for verification (don't include password in logs)
def print_config():
    print(f"Database Config:")
    print(f"  Host: {db_config.host}")
    print(f"  Port: {db_config.port}")
    print(f"  Database: {db_config.database}")
    print(f"  Username: {db_config.username}")
    print(f"  Password: {'*' * len(db_config.password)}")