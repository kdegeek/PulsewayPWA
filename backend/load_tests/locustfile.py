from locust import HttpUser, task

# This is the fallback API key used in backend/app/main.py if os.getenv("API_KEY") is None
# For a real load test, you might want to configure this via an environment variable
# or a more secure method if your Locust setup supports it.
TEST_API_KEY = "your-secret-key-here"

class DeviceMonitoringUser(HttpUser):
    """
    Simulates a user accessing device and monitoring dashboard endpoints.
    """
    # host = "http://localhost:8000" # Define host if not set from locust command line

    def on_start(self):
        """
        Called when a Locust start before any task is scheduled.
        Sets the API key header for all subsequent requests made by this user.
        """
        self.client.headers["X-API-Key"] = TEST_API_KEY
        # You could also add other default headers here if needed
        # self.client.headers["Content-Type"] = "application/json"

    @task(1) # (1) indicates the weight of this task; higher means more frequent
    def get_all_devices(self):
        """
        Task to fetch all devices.
        """
        self.client.get("/api/devices")

    @task(2) # This task will be picked twice as often as get_all_devices
    def get_monitoring_dashboard(self):
        """
        Task to fetch the monitoring dashboard summary.
        """
        self.client.get("/api/monitoring/dashboard")

    # You can add more tasks here, for example:
    # @task(1)
    # def get_device_stats(self):
    #     self.client.get("/api/devices/stats")

    # @task(1)
    # def get_specific_device(self):
    #     # This would require a list of known device IDs or a way to pick one.
    #     # For simplicity, keeping it out of the initial setup.
    #     # Example:
    #     # if self.environment.runner: # Check if running in a distributed environment
    #     #     device_id = self.environment.runner.stats.custom_stats.get("some_device_id_key")
    #     #     if device_id:
    #     #         self.client.get(f"/api/devices/{device_id}")
    #     # else: # Fallback for local running or if no shared ID mechanism
    #     #     pass # Or pick a hardcoded ID for local testing
    #     pass

# To run this locust file:
# 1. Ensure your FastAPI backend is running.
# 2. Install Locust: pip install locust
# 3. Navigate to the directory containing this locustfile.py (backend/load_tests/)
# 4. Run Locust: locust -f locustfile.py --host=http://localhost:8000 (or your app's host)
# 5. Open your browser to http://localhost:8089 (Locust's web UI) and start a new test.
#
# Example command to run from the project root (if backend/ is the app root):
# locust -f backend/load_tests/locustfile.py --host=http://localhost:8000
#
# If your FastAPI app is running inside Docker and port 8000 is exposed:
# locust -f backend/load_tests/locustfile.py --host=http://localhost:8000
#
# If you want to run Locust itself in Docker, you'd need a Dockerfile for Locust.
# For this task, it's assumed Locust is run from the host machine against the running backend.
