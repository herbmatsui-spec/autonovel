import time
import subprocess
import requests

def compose_up():
    """Start docker compose in detached mode."""
    subprocess.run(
        ["docker", "compose", "-f", "docker-compose.prod.yml", "up", "-d"],
        check=True,
    )

def compose_down():
    """Stop and remove containers, networks, and volumes."""
    subprocess.run(
        ["docker", "compose", "-f", "docker-compose.prod.yml", "down", "-v"],
        check=True,
    )

def wait_for_health(timeout=120):
    """Wait for the API health endpoint to return 200."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get("http://localhost:8000/health/live", timeout=5)
            if resp.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(5)
    raise TimeoutError("API health check failed")

def test_full_generation_flow():
    # Start the containers
    compose_up()
    try:
        # Wait for the API to be healthy
        wait_for_health()
        
        # Generation request
        test_payload = {
            "title": "Test Story",
            "genre": "fantasy",
            "length": "short"
        }
        resp = requests.post("http://localhost:8000/api/generate", json=test_payload, timeout=10)
        resp.raise_for_status()
        job_id = resp.json()["job_id"]
        
        # Poll for completion
        max_polls = 30
        poll_interval = 5
        for _ in range(max_polls):
            resp = requests.get(f"http://localhost:8000/api/jobs/{job_id}", timeout=10)
            resp.raise_for_status()
            job_status = resp.json()["status"]
            if job_status == "completed":
                break
            elif job_status == "failed":
                raise AssertionError("Job failed")
            time.sleep(poll_interval)
        else:
            raise TimeoutError("Job did not complete in time")
        
        # Result verification (assuming the job result endpoint)
        resp = requests.get(f"http://localhost:8000/api/jobs/{job_id}/result", timeout=10)
        resp.raise_for_status()
        result = resp.json()
        assert result["status"] == "success"
        assert len(result["text"]) > 100
        
        # Download
        zip_resp = requests.get(f"http://localhost:8000/api/download/{job_id}", timeout=10)
        assert zip_resp.status_code == 200
        assert zip_resp.headers["content-type"] == "application/zip"
    finally:
        # Clean up
        compose_down()