import sys
import os

# Ensure we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../04-backend")))

from app.workers.tasks import check_alerts_task

def main():
    try:
        print("Sending task to Celery...")
        result = check_alerts_task.delay()
        print(f"Task sent. ID: {result.id}")
        
        # Wait for the task to complete
        result_value = result.get(timeout=10)
        print(f"Task completed successfully! Result: {result_value}")
        sys.exit(0)
    except Exception as e:
        print(f"Celery smoke test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
