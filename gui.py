# gui.py
import tkinter as tk
from tkinter import ttk, messagebox
import uuid # For generating unique task IDs

# Assuming other modules are in the same directory orPYTHONPATH is set
import config_manager 
import scheduler 
# import gemini_client # Will be used by scheduler, not directly by GUI for now
# import email_sender # Will be used by scheduler

class App:
    def __init__(self, master):
        self.master = master
        master.title("Gemini Task Scheduler")
        master.protocol("WM_DELETE_WINDOW", self.on_closing) # Handle window close

        self.config = config_manager.load_config()
        self.tasks = self.config.get("scheduled_tasks", []) # Keep a local copy

        # --- Configuration Frame ---
        config_frame = ttk.LabelFrame(master, text="Configuration")
        config_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        ttk.Label(config_frame, text="Gemini API Key:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.api_key_var = tk.StringVar(value=self.config.get("gemini_api_key", ""))
        self.api_key_entry = ttk.Entry(config_frame, width=50, textvariable=self.api_key_var)
        self.api_key_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(config_frame, text="Default Recipient Email:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.email_var = tk.StringVar(value=self.config.get("recipient_email", ""))
        self.email_entry = ttk.Entry(config_frame, width=50, textvariable=self.email_var)
        self.email_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # SMTP Configuration Button (simplified for now)
        self.smtp_button = ttk.Button(config_frame, text="SMTP Settings (Placeholder)", command=self.open_smtp_settings)
        self.smtp_button.grid(row=2, column=0, columnspan=2, pady=5)


        # --- Frame for adding new tasks ---
        task_frame = ttk.LabelFrame(master, text="Add New Task")
        task_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        ttk.Label(task_frame, text="Prompt:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.prompt_text = tk.Text(task_frame, height=3, width=50)
        self.prompt_text.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(task_frame, text="Interval:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.interval_entry = ttk.Entry(task_frame, width=20)
        self.interval_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        # TODO: Add more sophisticated interval options (e.g., dropdown)
        ttk.Label(task_frame, text="(e.g., '1 hour', '1 day 10:00')").grid(row=1, column=1, padx=5, pady=5, sticky="e")


        self.search_internet_var = tk.BooleanVar()
        self.search_internet_check = ttk.Checkbutton(task_frame, text="Search Internet", variable=self.search_internet_var)
        self.search_internet_check.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        self.add_task_button = ttk.Button(task_frame, text="Add Task", command=self.add_task_gui)
        self.add_task_button.grid(row=3, column=1, padx=5, pady=5, sticky="e")

        # --- Frame for displaying tasks ---
        tasks_display_frame = ttk.LabelFrame(master, text="Scheduled Tasks")
        tasks_display_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")

        self.tasks_listbox = tk.Listbox(tasks_display_frame, height=10, width=70)
        self.tasks_listbox.pack(side=tk.LEFT, padx=(5,0), pady=5, fill=tk.BOTH, expand=True)
        
        # Scrollbar for listbox
        scrollbar = ttk.Scrollbar(tasks_display_frame, orient=tk.VERTICAL, command=self.tasks_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5, padx=(0,5))
        self.tasks_listbox.config(yscrollcommand=scrollbar.set)

        # Buttons for task management
        task_buttons_frame = ttk.Frame(tasks_display_frame)
        task_buttons_frame.pack(fill=tk.Y, padx=5, pady=5)

        self.remove_task_button = ttk.Button(task_buttons_frame, text="Remove Selected", command=self.remove_selected_task)
        self.remove_task_button.pack(pady=2, fill=tk.X)
        # TODO: Add Edit Task button

        # --- Controls ---
        control_frame = ttk.Frame(master)
        control_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

        self.start_button = ttk.Button(control_frame, text="Start Scheduler", command=self.start_scheduler_gui)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(control_frame, text="Stop Scheduler", command=self.stop_scheduler_gui, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        master.grid_columnconfigure(1, weight=1) # Allow second column to expand
        master.grid_rowconfigure(3, weight=1) # Allow task display frame to expand vertically
        tasks_display_frame.grid_columnconfigure(0, weight=1) # Allow listbox to expand horizontally

        self.update_tasks_listbox() # Load tasks from config into listbox

    def open_smtp_settings(self):
        # Placeholder for SMTP settings dialog
        # This would open a new Toplevel window to configure SMTP details
        # from self.config["smtp_settings"]
        messagebox.showinfo("SMTP Settings", "SMTP configuration dialog will be implemented here.\n"
                                           f"Current (dummy): {self.config['smtp_settings']['server']}")
                                           
    def save_main_config(self):
        """Saves the main configuration details (API key, email)"""
        self.config["gemini_api_key"] = self.api_key_var.get()
        self.config["recipient_email"] = self.email_var.get()
        # SMTP settings would be saved in their own dialog/logic
        if config_manager.save_config(self.config):
            print("Main configuration saved.")
        else:
            messagebox.showerror("Error", "Failed to save main configuration.")


    def add_task_gui(self):
        prompt = self.prompt_text.get("1.0", tk.END).strip()
        interval = self.interval_entry.get().strip()
        search_internet = self.search_internet_var.get()
        
        # Use global API key and recipient email by default for a task
        # These could be overridden per task if UI is expanded later
        api_key = self.api_key_var.get() 
        recipient_email = self.email_var.get()

        if not api_key:
            messagebox.showerror("Error", "Gemini API Key must be set in Configuration.")
            return
        if not recipient_email:
            messagebox.showerror("Error", "Default Recipient Email must be set in Configuration.")
            return
        if not prompt:
            messagebox.showerror("Error", "Prompt cannot be empty.")
            return
        if not interval: 
            messagebox.showerror("Error", "Interval cannot be empty.")
            return

        task_id = str(uuid.uuid4()) # Generate a unique ID for the task
        new_task = {
            "id": task_id,
            "prompt": prompt,
            "interval": interval,
            "search_internet": search_internet,
            "enabled": True # New tasks are enabled by default
            # api_key and recipient_email are implicitly global for now
            # if we want per-task overrides, they should be stored here too
        }
        
        if config_manager.add_task_to_config(new_task):
            self.tasks.append(new_task) # Update local cache
            self.update_tasks_listbox()
            messagebox.showinfo("Success", f"Task '{prompt[:30]}...' added.")
            # Clear input fields
            self.prompt_text.delete("1.0", tk.END)
            self.interval_entry.delete(0, tk.END)
            self.search_internet_var.set(False)
        else:
            messagebox.showerror("Error", "Failed to save task to configuration.")
            
    def remove_selected_task(self):
        selected_indices = self.tasks_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select a task to remove.")
            return

        # Assuming single selection for now
        selected_index = selected_indices[0]
        
        # Need to map listbox index to task ID, as listbox can be filtered/sorted later
        # For now, assuming direct mapping from self.tasks
        if 0 <= selected_index < len(self.tasks):
            task_to_remove = self.tasks[selected_index]
            task_id = task_to_remove.get("id")

            if not task_id:
                messagebox.showerror("Error", "Selected task has no ID. Cannot remove.")
                return

            confirm = messagebox.askyesno("Confirm Removal", 
                                         f"Are you sure you want to remove task:\n{task_to_remove['prompt'][:50]}...?")
            if confirm:
                if config_manager.remove_task_from_config(task_id):
                    self.tasks.pop(selected_index) # Update local cache
                    self.update_tasks_listbox()
                    messagebox.showinfo("Success", "Task removed.")
                    # If scheduler is running, we might need to tell it to update/remove this task
                    if scheduler._scheduler_thread and scheduler._scheduler_thread.is_alive():
                         scheduler.remove_task(task_id) # Tell running scheduler
                         print(f"GUI: Instructed running scheduler to remove task {task_id}")
                else:
                    messagebox.showerror("Error", "Failed to remove task from configuration.")
        else:
            messagebox.showerror("Error", "Invalid task selection.")


    def update_tasks_listbox(self):
        self.tasks_listbox.delete(0, tk.END)
        # self.tasks should be kept in sync with config_manager's tasks
        self.tasks = config_manager.get_tasks() # Refresh from source of truth
        
        for i, task in enumerate(self.tasks):
            status = "✓" if task.get("enabled", True) else "✗"
            display_text = f"{status} {task.get('id', 'NoID')[:8]} | {task['prompt'][:30]}... | {task['interval']}"
            if task['search_internet']:
                display_text += " (Net)"
            self.tasks_listbox.insert(tk.END, display_text)

    def start_scheduler_gui(self):
        self.save_main_config() # Save current API key and email before starting
        
        current_api_key = self.api_key_var.get()
        current_email_to = self.email_var.get()
        # SMTP config is loaded from self.config by the scheduler module if needed
        current_smtp_config = self.config.get("smtp_settings", {})

        if not current_api_key:
            messagebox.showerror("Error", "Gemini API Key is required in Configuration.")
            return
        if not current_email_to: # Assuming a default recipient is always needed
            messagebox.showerror("Error", "Default Recipient Email is required in Configuration.")
            return
        
        active_tasks = [task for task in self.tasks if task.get("enabled", True)]
        if not active_tasks:
            messagebox.showinfo("Info", "No enabled tasks to schedule.")
            return
            
        # Pass only enabled tasks to the scheduler
        scheduler.start_scheduler_thread(
            active_tasks, 
            current_api_key, 
            current_email_to, # This is the default email; tasks might override later if feature is added
            current_smtp_config
        )
        messagebox.showinfo("Scheduler", "Scheduler started with enabled tasks.")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.add_task_button.config(state=tk.DISABLED) # Prevent adding tasks while running
        self.remove_task_button.config(state=tk.DISABLED) # Prevent removing tasks while running


    def stop_scheduler_gui(self):
        scheduler.stop_scheduler_thread()
        messagebox.showinfo("Scheduler", "Scheduler stopped.")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.add_task_button.config(state=tk.NORMAL)
        self.remove_task_button.config(state=tk.NORMAL)

    def on_closing(self):
        """Handle window close event."""
        if messagebox.askokcancel("Quit", "Do you want to quit?\nThis will stop the scheduler if it's running."):
            self.save_main_config() # Save any changes in API key/email
            if scheduler._scheduler_thread and scheduler._scheduler_thread.is_alive():
                self.stop_scheduler_gui()
            self.master.destroy()


if __name__ == '__main__':
    # This is for testing the GUI in isolation.
    # Real application uses main.py
    root = tk.Tk()
    app = App(root)
    root.mainloop()
