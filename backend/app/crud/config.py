from sqlmodel import Session, select
from app.models import AIProviderConfig

def get_ai_provider_config(session: Session) -> AIProviderConfig | None:
    """Fetches the current AI provider configuration."""
    # There should only be one row with id=1
    return session.get(AIProviderConfig, 1)

def set_ai_provider_config(session: Session, provider_name: str) -> AIProviderConfig:
    """Sets the active AI provider name in the configuration."""
    config = session.get(AIProviderConfig, 1)
    if config:
        config.active_provider_name = provider_name
    else:
        # Create if it doesn't exist (should only happen once)
        config = AIProviderConfig(id=1, active_provider_name=provider_name)
    session.add(config)
    session.commit()
    session.refresh(config)
    return config 