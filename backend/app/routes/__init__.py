from .doctors import create_doctors_router
from .appointments import create_appointments_router
from .conversation import create_conversation_router
from .campaigns import create_campaigns_router
from .retell import create_retell_router
from .training import create_training_router

__all__ = [
    "create_doctors_router",
    "create_appointments_router",
    "create_conversation_router",
    "create_campaigns_router",
    "create_retell_router",
    "create_training_router",
]
