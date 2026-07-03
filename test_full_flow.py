import sys
import os
import asyncio
from unittest.mock import MagicMock
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.getcwd(), "backend", ".env"))

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.client_manager import ClientManager
from app.services.conversation_orchestrator import ConversationOrchestrator
from app.services.groq_service import GroqService
from app.services.prompt_manager import PromptManager
from app.services.booking_service import BookingService
from app.services.doctor_service import DoctorService

async def test_full_flow():
    print("--- Initializing Services ---")
    client_manager = ClientManager()
    prompt_manager = PromptManager()
    
    client_id = "akira_eye_hospital_amalapuram"
    
    groq_api_key = os.environ.get("GROQ_API_KEY")
    if not groq_api_key:
        print("ERROR: GROQ_API_KEY not found in environment")
        return
    
    groq_service = GroqService(
        api_key=groq_api_key,
        model=os.environ.get("GROQ_MODEL", "mixtral-8x7b-32768")
    )
    
    sheets_service = MagicMock()
    doctor_service = DoctorService(sheets_service)
    booking_service = BookingService(sheets_service, doctor_service)
    
    orchestrator = ConversationOrchestrator(
        groq_service=groq_service,
        prompt_manager=prompt_manager,
        client_manager=client_manager,
        booking_service=booking_service,
        doctor_service=doctor_service
    )
    
    print("--- Processing Iteration 1 ---")
    try:
        result = await orchestrator.process_conversation(
            user_input="Naaku eye doctor appointment kavali",
            client_id=client_id,
            conversation_id="conv_001"
        )
        print(f"Result success: {result.get('success')}")
        if result.get('success'):
            print(f"AI Response: {result.get('response')}")
        else:
            print(f"Error: {result.get('error')}")

        print("\n--- Processing Iteration 2 (Checking Memory) ---")
        result2 = await orchestrator.process_conversation(
            user_input="Eroju evening ki kavali",
            client_id=client_id,
            conversation_id="conv_001"
        )
        print(f"Result 2 success: {result2.get('success')}")
        if result2.get('success'):
            print(f"AI Response 2: {result2.get('response')}")
        else:
            print(f"Error 2: {result2.get('error')}")

    except Exception as e:
        print(f"Uncaught exception: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_full_flow())
