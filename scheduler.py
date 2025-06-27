# scheduler.py
import time
import threading
import schedule
import datetime # Added for next_run calculations
import traceback # For detailed error logging

# This will hold the jobs managed by the schedule library
_jobs = []
_scheduler_thread = None
_stop_event = threading.Event()

# Placeholder for functions that will be called by the scheduler
# These would typically interact with gemini_client and email_sender
from gemini_client import GeminiClient # Import at module level
from email_sender import EmailSender # Import at module level

def _task_execution_function(task_id, prompt, search_internet, email_to, api_key, smtp_config):
    """
    This function is what the scheduler will execute for each task.
    1. Get response from Gemini (using gemini_client)
    2. Send email with the response (using email_sender)
    """
    print(f"Scheduler INFO: Executing task '{task_id}' at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Task Details - Prompt: '{prompt}', Search Internet: {search_internet}, Email To: {email_to}")
    
    # --- Gemini Interaction ---
    gemini_interaction_successful = False
    response = ""
    try:
        print(f"Scheduler INFO: Task '{task_id}' - Initializing GeminiClient.")
        gemini = GeminiClient(api_key=api_key)
        print(f"Scheduler INFO: Task '{task_id}' - Requesting response from Gemini.")
        response = gemini.get_gemini_response(prompt, search_internet)

        if response and not response.startswith("Error:"):
            gemini_interaction_successful = True
            print(f"Scheduler SUCCESS: Task '{task_id}' - Successfully received response from Gemini: '{response[:100]}...'")
        else:
            # GeminiClient already logs its own errors. This log indicates the scheduler's perspective.
            print(f"Scheduler ERROR: Task '{task_id}' - Failed to get a valid response from Gemini. Received: '{response}'")
            # Optional: could set a default error response for the email if needed
            # response = "Error: Could not retrieve response from Gemini."
    except Exception as e_gemini:
        print(f"Scheduler CRITICAL: Task '{task_id}' - Exception during Gemini interaction: {e_gemini}")
        traceback.print_exc()
        response = f"Error: Exception occurred while contacting Gemini: {e_gemini}"

    if not gemini_interaction_successful:
        # If Gemini interaction failed, we might still want to send an email notification
        # or simply log and not send an email. For now, let's assume we send an email
        # with the error message if an email address is configured.
        print(f"Scheduler WARNING: Task '{task_id}' - Proceeding to email step despite Gemini interaction failure.")
        # If response is empty due to an exception, ensure it has some content.
        if not response: response = "Error: Unknown issue during Gemini interaction, no response obtained."

    # --- Email Sending ---
    email_sent_successfully = False
    if not email_to:
        print(f"Scheduler INFO: Task '{task_id}' - No recipient email configured. Skipping email send.")
    elif not (smtp_config and smtp_config.get("server") and smtp_config.get("user")):
        print(f"Scheduler WARNING: Task '{task_id}' - SMTP configuration incomplete. Skipping email send. Config: {smtp_config}")
    else:
        try:
            print(f"Scheduler INFO: Task '{task_id}' - Initializing EmailSender for {smtp_config.get('user')}@{smtp_config.get('server')}.")
            sender = EmailSender(
                smtp_server=smtp_config["server"],
                smtp_port=int(smtp_config["port"]),
                smtp_user=smtp_config["user"],
                smtp_password=smtp_config["password"],
                use_tls=smtp_config.get("use_tls", True)
            )
            subject_prefix = "Gemini Task Result"
            if not gemini_interaction_successful:
                 subject_prefix = "Gemini Task Alert - Error"
            subject = f"{subject_prefix}: {prompt[:30]}..."

            body_html = f"<html><body><h1>{subject_prefix}</h1><p><b>Task ID:</b> {task_id}</p><p><b>Prompt:</b> {prompt}</p><hr><h3>Response:</h3><p>{response.replace('n', '<br>')}</p></body></html>"
            body_text = f"{subject_prefix}\nTask ID: {task_id}\nPrompt: {prompt}\n\nResponse:\n{response}"

            print(f"Scheduler INFO: Task '{task_id}' - Attempting to send email to {email_to} with subject '{subject}'.")
            if sender.send_email(email_to, subject, body_html, body_text):
                print(f"Scheduler SUCCESS: Task '{task_id}' - Email successfully sent to {email_to}.")
                email_sent_successfully = True
            else:
                # EmailSender logs specific errors. This is the scheduler's summary.
                print(f"Scheduler ERROR: Task '{task_id}' - Failed to send email to {email_to} (EmailSender returned false). Check EmailSender logs.")

        except ImportError: # Should not happen if EmailSender imported at module level
            print(f"Scheduler CRITICAL: Task '{task_id}' - EmailSender module not found during task execution. This is unexpected.")
        except KeyError as e_key:
            print(f"Scheduler ERROR: Task '{task_id}' - Missing key in smtp_config: {e_key}. Cannot send email.")
        except Exception as e_email:
            print(f"Scheduler CRITICAL: Task '{task_id}' - An unexpected error occurred during email sending: {e_email}")
            traceback.print_exc()

    # --- Update Config with Last Run Details (if email was intended and successful, or even if Gemini failed but email was attempted) ---
    # We update config if the Gemini part produced a response (even an error string)
    # and an email attempt was made (or would have been made if configured).
    # This helps track that the task ran, regardless of full success.
    if response: # If there's any response (success or error string from Gemini part)
        try:
            import config_manager # Local import for safety, though less critical now
            current_time_iso = datetime.datetime.now().isoformat()
            # Save the Gemini response (which might be an error message) and the time
            print(f"Scheduler INFO: Task '{task_id}' - Attempting to update last run details in config.")
            if config_manager.update_task_last_run_details(task_id, response, current_time_iso):
                print(f"Scheduler INFO: Task '{task_id}' - Last run details (response/time) updated in config.")
            else:
                print(f"Scheduler WARNING: Task '{task_id}' - Failed to update last run details in config (task ID not found or save error).")
        except ImportError:
            print(f"Scheduler ERROR: Task '{task_id}' - ConfigManager module not found. Cannot update task details.")
        except Exception as e_conf:
            print(f"Scheduler ERROR: Task '{task_id}' - Unexpected error updating task details in config: {e_conf}")
            traceback.print_exc()

    print(f"Scheduler INFO: --- Task '{task_id}' execution finished ---")


def _parse_interval(interval_str):
    """
    Parses an interval string in the format "N unit" (e.g., "5 minutes", "1 hour", "2 days", "3 weeks")
    and configures a schedule object (e.g., schedule.every(N).minutes).
    This configured schedule object is then returned, ready for a .do() call.
    Returns a configured schedule.Scheduler object or None if parsing fails.
    
    Supported units: "minutes", "hours", "days", "weeks" (and their singular forms).
    The value N must be a positive integer.
    """
    parts = interval_str.lower().split() # e.g., "5 minutes" -> ["5", "minutes"]
    job = schedule.every()
    
    if len(parts) != 2:
        print(f"Scheduler: Invalid interval format: '{interval_str}'. Expected 'N unit' (e.g., '10 minutes').")
        return None

    try:
        value = int(parts[0])
        unit = parts[1]

        if value <= 0:
            print(f"Scheduler: Interval value must be a positive integer, got: {value} from '{interval_str}'")
            return None

        # Create a scheduler setup, e.g., schedule.every(value)
        current_job_setup = schedule.every(value)

        # Then chain the unit method, e.g., current_job_setup.minutes
        if unit in ["minute", "minutes"]:
            current_job_setup.minutes
        elif unit in ["hour", "hours"]:
            current_job_setup.hours
        elif unit in ["day", "days"]:
            current_job_setup.days
            # Note: If specific times for daily tasks (e.g., "every day at 10:00") are needed,
            # the GUI would need to provide this, and this parser would need to be extended.
        elif unit in ["week", "weeks"]:
            current_job_setup.weeks
        else:
            print(f"Scheduler: Unknown interval unit: '{unit}' in '{interval_str}'. Supported: minutes, hours, days, weeks.")
            return None

        return current_job_setup # This is a configured Scheduler object, not a Job yet.
                                 # .do() will be called on this by the add_task function.
    except ValueError: # Handles non-integer for value
        print(f"Scheduler: Invalid interval number: '{parts[0]}' in '{interval_str}'. Must be an integer.")
        return None
    except Exception as e: # Catch-all for other unexpected errors during parsing
        print(f"Scheduler: Unexpected error parsing interval '{interval_str}': {e}")
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
            _task_execution_function,
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
    """
    Lists all currently scheduled tasks, providing their ID, next run time,
    and a formatted string for the time remaining until the next run.

    Returns:
        list: A list of dictionaries, where each dictionary contains:
              - "id" (str): The unique ID of the task.
              - "next_run_iso" (str | None): ISO formatted string of the next run datetime, or None.
              - "time_remaining_str" (str): Formatted countdown string (e.g., "01:23:45",
                                            "Running/Overdue", or "N/A").
              - "job_str" (str): String representation of the schedule job object for debugging.
    """
    if not schedule.jobs:
        print("DEBUG: scheduler.py -> list_tasks -> No jobs in schedule.jobs")
        return [] # No jobs scheduled

    tasks_info = []
    now = datetime.datetime.now() # Current time, fetched once for consistency in calculations

    print(f"DEBUG: scheduler.py -> list_tasks -> Current schedule.jobs: {schedule.jobs}")

    for job in schedule.jobs:
        if not job.tags: # Each job should be tagged with its task_id
            print(f"Scheduler Warning: Found a job with no tags: {job}")
            continue

        task_id = list(job.tags)[0] # Assume the first tag is the unique task ID
        next_run_dt = job.next_run  # datetime object for the next scheduled execution

        time_remaining_str = "N/A" # Default if next_run_dt is None
        if next_run_dt:
            if next_run_dt > now: # If the next run is in the future
                time_remaining = next_run_dt - now # timedelta object
                total_seconds = int(time_remaining.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                time_remaining_str = f"{hours:02}:{minutes:02}:{seconds:02}" # HH:MM:SS format
            else: # If the next run is in the past or now
                time_remaining_str = "Running/Overdue"

        tasks_info.append({
            "id": task_id,
            "next_run_iso": next_run_dt.isoformat() if next_run_dt else None,
            "time_remaining_str": time_remaining_str,
            "job_str": str(job) # Useful for debugging the raw schedule job
        })
    return tasks_info

def get_task_status_by_id(task_id_to_find):
    """
    Gets status (next run time, time remaining) for a specific task by its ID.
    This is similar to list_tasks but filtered for a single task.

    Args:
        task_id_to_find (str): The ID of the task to find.

    Returns:
        dict | None: A dictionary with task status details (similar to list_tasks items)
                      if found, otherwise None.
    """
    for job in schedule.jobs:
        if task_id_to_find in job.tags:
            now = datetime.datetime.now()
            next_run_dt = job.next_run
            time_remaining_str = "N/A"
            if next_run_dt:
                if next_run_dt > now:
                    time_remaining = next_run_dt - now
                    total_seconds = int(time_remaining.total_seconds())
                    hours, remainder = divmod(total_seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    time_remaining_str = f"{hours:02}:{minutes:02}:{seconds:02}"
                else:
                    time_remaining_str = "Running/Overdue"
            return { # Return structure matches items from list_tasks
                "id": task_id_to_find,
                "next_run_iso": next_run_dt.isoformat() if next_run_dt else None,
                "time_remaining_str": time_remaining_str,
                "job_str": str(job)
            }
    return None # Task not found


def _run_scheduler():
    """Target function for the scheduler thread."""
    print("Scheduler: Scheduler thread started.")
    _stop_event.clear()
    while not _stop_event.is_set():
        try:
            schedule.run_pending()
        except Exception as e:
            print(f"Scheduler Error: Exception in run_pending loop: {type(e).__name__}: {e}")
            traceback.print_exc() # Print full traceback to console
            # Depending on the severity or type of error, we might want to stop the scheduler.
            # For now, it will log and continue, which might lead to repeated errors if the cause persists.
            # Consider adding specific error handling or a flag to stop on repeated/critical errors.

        # Detailed log for each loop iteration
        is_stopped = _stop_event.is_set()
        num_jobs = len(schedule.jobs)
        # print(f"Scheduler DEBUG: Loop iteration. stop_event set? {is_stopped}, Current jobs in schedule: {num_jobs}")
        # Reducing verbosity for now, enable if needed:
        if num_jobs == 0 and not is_stopped:
            print(f"Scheduler DEBUG: Loop iteration. stop_event set? {is_stopped}, No jobs in schedule. Next check in 1s.")


        time.sleep(1) # Check for pending jobs every second

    # This part is reached when _stop_event is set
    print("Scheduler: Scheduler thread stopping gracefully (loop condition met).")
    schedule.clear() # Clear all jobs from the schedule instance
    _jobs.clear() # Clear our internal list of job objects
    print("Scheduler: All scheduled jobs cleared.")


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

    print(f"DEBUG: scheduler.py -> start_scheduler_thread -> Received tasks_to_schedule: {tasks_to_schedule}")

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
    print("DEBUG: scheduler.py -> stop_scheduler_thread() CALLED") # DEBUG LOG
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        print("Scheduler: Attempting to stop scheduler thread...")
        _stop_event.set()
        print(f"Scheduler DEBUG: _stop_event was set to {_stop_event.is_set()}")
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
