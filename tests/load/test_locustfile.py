from locust import HttpUser, task, between
import random

class WebsiteUser(HttpUser):
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks

    @task
    def generate_story(self):
        # Step 1: Generate a story
        payload = {
            "title": f"Test Story {random.randint(1, 1000)}",
            "genre": random.choice(["fantasy", "sci-fi", "romance", "mystery"]),
            "length": random.choice(["short", "medium", "long"]),
        }
        with self.client.post("/api/generate", json=payload, catch_response=True) as response:
            if response.status_code == 202:
                job_id = response.json()["job_id"]
                # Step 2: Poll for completion
                for _ in range(10):  # Poll up to 10 times
                    response = self.client.get(f"/api/jobs/{job_id}")
                    if response.status_code == 200:
                        job_data = response.json()
                        if job_data["status"] == "completed":
                            # Step 3: Download the result
                            self.client.get(f"/api/download/{job_id}")
                            break
                        elif job_data["status"] == "failed":
                            break
                    # Wait before next poll
                    self.wait_time()
            else:
                response.failure(f"Failed to generate story: {response.status_code}")