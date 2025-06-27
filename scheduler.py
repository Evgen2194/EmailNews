# scheduler.py
import time
import threading
import schedule

# This will hold the jobs managed by the schedule library
_jobs = []
_scheduler_thread = None
_stop_event = threading.Event()

# Placeholder for functions that will be called by the scheduler
# These would typically interact with gemini_client and email_sender

def _placeholder_task_function(task_id, prompt, search_internet, email_to, api_key, smtp_config):
    """
    This function is what the scheduler will execute for each task.
    It needs to:
    1. Get response from Gemini (using gemini_client)
    2. Send email with the response (using email_sender)
    """
    print(f"Scheduler: Executing task {task_id} at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Prompt: {prompt}")
    print(f"  Search Internet: {search_internet}")
    print(f"  Email To: {email_to}")
    print(f"  API Key used: {'*' * len(api_key) if api_key else 'None'}")
    
    # --- Simulate Gemini Interaction ---
    # In real implementation, you'd import and use GeminiClient
    # from gemini_client import GeminiClient
    # gemini = GeminiClient(api_key=api_key)
    # response = gemini.get_gemini_response(prompt, search_internet)
    response = f"Simulated Gemini response for '{prompt}' obtained at {time.strftime('%H:%M:%S')}."
    if search_internet:
        response = f"(Simulated search done) {response}"
    print(f"  Simulated Gemini Response: {response}")

    # --- Email Sending ---
    if smtp_config and smtp_config.get("server") and smtp_config.get("user"): # Basic check
        try:
            from email_sender import EmailSender # Import here to avoid circular deps if any at module level

            sender = EmailSender(
                smtp_server=smtp_config["server"],
                smtp_port=int(smtp_config["port"]), # Ensure port is int
                smtp_user=smtp_config["user"],
                smtp_password=smtp_config["password"],
                use_tls=smtp_config.get("use_tls", True)
            )
            subject = f"Scheduled Gemini Response: {prompt[:30]}..."

            # For now, sending HTML and Text as the same.
            # Could refine to generate a simpler text version.
            body_html = f"<html><body><h1>Gemini Task Result</h1><p><b>Prompt:</b> {prompt}</p><hr><p>{response.replace('n', '<br>')}</p></body></html>"
            body_text = f"Gemini Task Result\nPrompt: {prompt}\n\nResponse:\n{response}"

            print(f"  Attempting to send email to {email_to} via {smtp_config['user']}@{smtp_config['server']}...")
            if sender.send_email(email_to, subject, body_html, body_text):
                print(f"  Email successfully sent to {email_to}.")
            else:
                print(f"  Failed to send email to {email_to}. Check EmailSender logs.")
        except ImportError:
            print("  EmailSender module not found. Cannot send email.")
        except KeyError as e:
            print(f"  Email sending skipped: Missing key in smtp_config: {e}. Full config: {smtp_config}")
        except Exception as e:
            print(f"  An error occurred during email sending: {e}")
    else:
        print(f"  Email sending skipped: SMTP configuration is incomplete or missing. Config: {smtp_config}")

    print("--- Task execution finished ---")


def _parse_interval(interval_str):
    """
    Parses an interval string (e.g., "5 seconds", "1 minute", "1 hour", "1 day 10:00")
    and configures a schedule job.
    Returns a schedule.Job object or None if parsing fails.
    
    This is a simplified parser. A more robust solution might use regex
    or a dedicated parsing library.
    """
    parts = interval_str.lower().split()
    job = schedule.every()
    
    try:
        if "second" in parts[1]:
            job = job.seconds(int(parts[0]))
        elif "minute" in parts[1]:
            job = job.minutes(int(parts[0]))
        elif "hour" in parts[1]:
            job = job.hours(int(parts[0]))
        elif "day" in parts[1]:
            if len(parts) > 2 and ":" in parts[2]: # e.g., "1 day 10:00"
                job = job.day.at(parts[2])
            else: # e.g., "1 day" or "days"
                job = job.days(int(parts[0])) # Assumes "days" if just a number
        # Add more specific cases like "weekly", "monday at 10:00" etc. if needed
        # e.g. job.monday.at("10:30")
        else:
            print(f"Scheduler: Could not parse interval string: {interval_str}")
            return None
        return job
    except (IndexError, ValueError) as e:
        print(f"Scheduler: Error parsing interval '{interval_str}': {e}")
        return None

def add_task(task_id, prompt, interval_str, search_internet, email_to, api_key, smtp_config):
    """
    Adds a new task to the scheduler.
    task_id: A unique identifier for the task.
    """
    parsed_job = _parse_interval(interval_str)
    if parsed_job:
        # Using a lambda to pass arguments to the task function
        # Each job needs its own set of arguments captured at the time of scheduling
        job_instance = parsed_job.do(
            _placeholder_task_function, 
            task_id=task_id,
            prompt=prompt, 
            search_internet=search_internet, 
            email_to=email_to,
            api_key=api_key,
            smtp_config=smtp_config # This would be the global SMTP config
        )
        job_instance.tag(task_id) # Tag the job with its ID for later management
        _jobs.append(job_instance)
        print(f"Scheduler: Task '{task_id}' ({prompt[:20]}...) scheduled with interval '{interval_str}'. Job: {job_instance}")
        return True
    else:
        print(f"Scheduler: Failed to schedule task '{task_id}' due to interval parsing error.")
        return False

def remove_task(task_id):
    """Removes a task from the scheduler by its ID."""
    schedule.clear(task_id) # Clears jobs with this specific tag
    # Also remove from our internal _jobs list if necessary, though schedule.clear should handle it.
    _jobs[:] = [j for j in _jobs if task_id not in j.tags]
    print(f"Scheduler: Task '{task_id}' removed.")

def list_tasks():
    """Lists all currently scheduled tasks."""
    if not schedule.jobs:
        print("Scheduler: No tasks currently scheduled.")
        return []
    tasks_info = []
    for job in schedule.jobs:
        tasks_info.append(str(job)) # Basic representation, can be improved
    return tasks_info

def _run_scheduler():
    """Target function for the scheduler thread."""
    print("Scheduler: Scheduler thread started.")
    _stop_event.clear()
    while not _stop_event.is_set():
        schedule.run_pending()
        time.sleep(1) # Check for pending jobs every second
    print("Scheduler: Scheduler thread stopped.")
    schedule.clear() # Clear all jobs when stopping
    _jobs.clear()


def start_scheduler_thread(tasks_to_schedule, global_api_key, global_email_to, global_smtp_config):
    """
    Starts the scheduler in a separate thread.
    tasks_to_schedule: A list of task dictionaries (from gui.py or config)
                       Each dict: {"id": "task_1", "prompt": "...", "interval": "...", ...}
    global_api_key, global_email_to, global_smtp_config: Configurations from the UI/config file.
    """
    global _scheduler_thread, _stop_event

    if _scheduler_thread and _scheduler_thread.is_alive():
        print("Scheduler: Scheduler is already running.")
        return

    print("Scheduler: Starting scheduler...")
    _stop_event = threading.Event() # Ensure a fresh event

    # Clear any previous jobs before starting
    schedule.clear()
    _jobs.clear()

    for i, task_config in enumerate(tasks_to_schedule):
        # Assuming task_config has 'prompt', 'interval', 'search_internet'
        # And we use global settings for api_key, email_to (or task-specific if available)
        task_id = task_config.get("id", f"task_{i+1}") # Generate an ID if not present
        
        # Use task-specific API key and email if provided, otherwise global
        api_key_to_use = task_config.get("api_key", global_api_key)
        email_to_use = task_config.get("email_to", global_email_to)

        add_task(
            task_id=task_id,
            prompt=task_config["prompt"],
            interval_str=task_config["interval"],
            search_internet=task_config["search_internet"],
            email_to=email_to_use,
            api_key=api_key_to_use,
            smtp_config=global_smtp_config
        )
    
    if not _jobs:
        print("Scheduler: No tasks provided to schedule.")
        # Decide if we should start the thread anyway or not. For now, let's start it.
        # return

    _scheduler_thread = threading.Thread(target=_run_scheduler, daemon=True)
    _scheduler_thread.start()

def stop_scheduler_thread():
    """Stops the scheduler thread."""
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        print("Scheduler: Stopping scheduler thread...")
        _stop_event.set()
        _scheduler_thread.join(timeout=5) # Wait for the thread to finish
        if _scheduler_thread.is_alive():
            print("Scheduler: Thread did not stop in time.")
        else:
            print("Scheduler: Thread stopped successfully.")
        _scheduler_thread = None
        schedule.clear() # Ensure all jobs are cleared
        _jobs.clear()
    else:
        print("Scheduler: Scheduler thread is not running.")

if __name__ == '__main__':
    # Example Usage (for testing this module directly)
    print("Testing Scheduler...")

    # Dummy config
    dummy_smtp_config = {"host": "smtp.example.com", "port": 587}
    dummy_api_key_main = "MAIN_API_KEY"
    dummy_email_main = "main_recipient@example.com"

    tasks_data = [
        {"id": "joke_task", "prompt": "Tell me a joke", "interval": "5 seconds", "search_internet": False},
        {"id": "news_task", "prompt": "Latest AI news", "interval": "10 seconds", "search_internet": True, "api_key": "TASK_SPECIFIC_KEY"},
        {"id": "weather_task", "prompt": "Weather in London", "interval": "1 day 08:00", "search_internet": True, "email_to": "weather_fan@example.com"},
        {"id": "bad_interval_task", "prompt": "This won't run", "interval": "every blue moon", "search_internet": False},
    ]

    start_scheduler_thread(tasks_data, dummy_api_key_main, dummy_email_main, dummy_smtp_config)

    print("\nScheduled jobs:")
    for job_info in list_tasks():
        print(job_info)
    
    print("\nScheduler running for 22 seconds... Check console for task executions.")
    try:
        time.sleep(12)
        print("\n--- Removing 'joke_task' ---")
        remove_task("joke_task")
        print("\nScheduled jobs after removal:")
        for job_info in list_tasks():
            print(job_info)
        time.sleep(10)
    except KeyboardInterrupt:
        print("Scheduler test interrupted by user.")
    finally:
        stop_scheduler_thread()
        print("Scheduler test complete.")
