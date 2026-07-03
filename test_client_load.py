import sys
import os
import json

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.client_manager import ClientManager

def test_load():
    cm = ClientManager()
    print(f"Loaded clients: {cm.list_clients()}")
    
    client_id = "akira_eye_hospital_amalapuram"
    if cm.client_exists(client_id):
        print(f"SUCCESS: {client_id} found!")
        print(f"Metadata: {json.dumps(cm.get_client_metadata(client_id), indent=2)}")
    else:
        print(f"FAILURE: {client_id} not found.")
        
        # Check why it's not found
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(cm.__class__.__init__.__code__.co_filename if hasattr(cm.__class__.__init__.__code__, 'co_filename') else "__file__"))))
        print(f"Scanning base_dir manually...")

if __name__ == "__main__":
    test_load()
