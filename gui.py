# gui.py
import tkinter as tk
from tkinter import ttk, messagebox
import uuid # For generating unique task IDs

# Assuming other modules are in the same directory orPYTHONPATH is set
import config_manager 
import scheduler 
# import gemini_client # Will be used by scheduler, not directly by GUI for now
from email_sender import EmailSender # Will be used by GUI for test email

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
        
        # SMTP Configuration Button
        self.smtp_button = ttk.Button(config_frame, text="SMTP Settings", command=self.open_smtp_settings_dialog)
        self.smtp_button.grid(row=2, column=0, columnspan=2, pady=(5,0)) # Reduced bottom padding

        # --- Test Email Frame ---
        test_email_frame = ttk.LabelFrame(config_frame, text="Test Email Sending")
        test_email_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        ttk.Label(test_email_frame, text="Test Recipient:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.test_email_recipient_var = tk.StringVar(value=self.config.get("recipient_email", ""))
        self.test_email_recipient_entry = ttk.Entry(test_email_frame, width=40, textvariable=self.test_email_recipient_var)
        self.test_email_recipient_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.send_test_email_button = ttk.Button(test_email_frame, text="Send Test Email", command=self.send_test_email)
        self.send_test_email_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        test_email_frame.columnconfigure(1, weight=1) # Allow entry to expand


        # --- Frame for adding new tasks ---
        task_frame = ttk.LabelFrame(master, text="Add New Task")
        task_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        ttk.Label(task_frame, text="Prompt:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.prompt_text = tk.Text(task_frame, height=3, width=50)
        self.prompt_text.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Interval Input Section
        interval_label_frame = ttk.Frame(task_frame) # Frame to group interval widgets
        interval_label_frame.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(task_frame, text="Interval:").grid(row=1, column=0, padx=5, pady=5, sticky="w") # Label for the whole row

        ttk.Label(interval_label_frame, text="Every:").pack(side=tk.LEFT, padx=(0,2)) # "Every"

        self.interval_value_var = tk.StringVar(value="1") # Variable for the numeric part of interval
        self.interval_value_entry = ttk.Entry(interval_label_frame, width=5, textvariable=self.interval_value_var) # Entry for number
        self.interval_value_entry.pack(side=tk.LEFT, padx=(0,5))

        self.interval_unit_var = tk.StringVar() # Variable for the unit part of interval
        self.interval_units = ["Minutes", "Hours", "Days", "Weeks"] # Available units
        self.interval_unit_combobox = ttk.Combobox(interval_label_frame, textvariable=self.interval_unit_var,
                                                 values=self.interval_units, width=10, state="readonly") # Combobox for units
        self.interval_unit_combobox.pack(side=tk.LEFT)
        self.interval_unit_combobox.set(self.interval_units[0]) # Default to "Minutes"

        # Old example usage label, commented out as new UI is more explicit
        # ttk.Label(task_frame, text="(e.g., '1 hour', '1 day 10:00')").grid(row=1, column=1, padx=5, pady=5, sticky="e")


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

        # TODO: Add Edit Task button (consider how it interacts with running tasks)
        # TODO: Add Enable/Disable Task button

        # --- Task Details / Status Frame ---
        self.task_details_frame = ttk.LabelFrame(master, text="Task Status & Details")
        self.task_details_frame.grid(row=3, column=2, padx=10, pady=5, sticky="nsew")

        self.details_last_sent_var = tk.StringVar(value="Last Sent: N/A")
        ttk.Label(self.task_details_frame, textvariable=self.details_last_sent_var).pack(anchor="w", padx=5, pady=2)

        ttk.Label(self.task_details_frame, text="Last Response:").pack(anchor="w", padx=5, pady=(5,0))
        self.details_last_response_text = tk.Text(self.task_details_frame, height=8, width=40, wrap=tk.WORD, state=tk.DISABLED)
        self.details_last_response_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        # Make the text widget expand
        self.task_details_frame.grid_rowconfigure(1, weight=1) # Assuming Last Response Text is effectively row 1 after labels
        self.task_details_frame.grid_columnconfigure(0, weight=1)


        # --- Frame for task actions (Enable/Disable) ---
        # Placed below tasks_display_frame (row=3) and above control_frame
        task_actions_frame = ttk.Frame(master)
        task_actions_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=(5,0), sticky="ew") 

        self.enable_task_button = ttk.Button(task_actions_frame, text="Enable Selected", command=self.enable_selected_task, state=tk.DISABLED)
        self.enable_task_button.pack(side=tk.LEFT, padx=5)

        self.disable_task_button = ttk.Button(task_actions_frame, text="Disable Selected", command=self.disable_selected_task, state=tk.DISABLED)
        self.disable_task_button.pack(side=tk.LEFT, padx=5)

        # --- Controls (Start/Stop Scheduler, Remove Task) ---
        # Placed below task_actions_frame
        control_frame = ttk.Frame(master)
        control_frame.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.start_button = ttk.Button(control_frame, text="Start Scheduler", command=self.start_scheduler_gui)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(control_frame, text="Stop Scheduler", command=self.stop_scheduler_gui, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.remove_task_button = ttk.Button(control_frame, text="Remove Selected Task", command=self.remove_selected_task)
        self.remove_task_button.pack(side=tk.LEFT, padx=15) 
        
        master.grid_columnconfigure(1, weight=1) # Allow task list to expand (col 0 is label)
        master.grid_columnconfigure(2, weight=1) # Allow task details to expand
        master.grid_rowconfigure(3, weight=1) # Allow task display frame (row containing listbox and details) to expand vertically
        tasks_display_frame.grid_columnconfigure(0, weight=1) # Allow listbox to expand horizontally
        self.task_details_frame.grid_rowconfigure(2, weight=1) # Ensure Text widget can expand
        self.task_details_frame.grid_columnconfigure(0, weight=1)


        self.tasks_listbox.bind('<<ListboxSelect>>', self.on_task_select)
        self.update_tasks_listbox() # Load tasks from config into listbox
        self.clear_task_details() # Initialize details pane
        self.master.after(1000, self.periodic_update_tasks_display) # Start periodic updates for countdowns and details

    def send_test_email(self):
        """Sends a test email using the configured SMTP settings."""
        # Ensure current config (especially SMTP settings) is up-to-date
        # self.save_main_config() # Main config (API key, default email) might not be relevant here
        # SMTP settings are directly from self.config or loaded if SMTP dialog was used.
        
        smtp_settings = self.config.get("smtp_settings")
        test_recipient = self.test_email_recipient_var.get().strip()

        if not test_recipient:
            messagebox.showerror("Error", "Test Recipient Email cannot be empty.", parent=self.master)
            return

        if not smtp_settings or not all(smtp_settings.get(k) for k in ["server", "port", "user"]):
            messagebox.showerror("Error", "SMTP settings are incomplete. Please configure them via 'SMTP Settings'.", parent=self.master)
            return
        
        # Password can be empty for some SMTP setups, so we don't strictly check its presence here,
        # but EmailSender will require it if the server does.

        print(f"GUI INFO: Attempting to send test email to {test_recipient} using SMTP: {smtp_settings['user']}@{smtp_settings['server']}")

        try:
            sender = EmailSender(
                smtp_server=smtp_settings["server"],
                smtp_port=int(smtp_settings["port"]), # Ensure port is int
                smtp_user=smtp_settings["user"],
                smtp_password=smtp_settings.get("password", ""), # Get password, could be empty
                use_tls=smtp_settings.get("use_tls", True),
                use_ssl=smtp_settings.get("use_ssl", False) # Pass the new SSL setting
            )
            
            subject = "Test Email from Gemini Task Scheduler"
            body_html = """
            <html><body>
                <h1>Test Email</h1>
                <p>This is a test email sent from the Gemini Task Scheduler application.</p>
                <p>If you received this, your SMTP settings are likely configured correctly!</p>
            </body></html>
            """
            body_text = "Test Email\n\nThis is a test email sent from the Gemini Task Scheduler application.\nIf you received this, your SMTP settings are likely configured correctly!"

            if sender.send_email(test_recipient, subject, body_html, body_text):
                messagebox.showinfo("Success", f"Test email sent successfully to {test_recipient}.", parent=self.master)
            else:
                # EmailSender already prints detailed errors to console.
                messagebox.showerror("Failure", f"Failed to send test email to {test_recipient}.\nCheck console logs from EmailSender for details.", parent=self.master)
        except ValueError as ve: # For int(smtp_settings["port"])
            messagebox.showerror("Error", f"Invalid SMTP port configured: {smtp_settings.get('port')}. Must be a number.", parent=self.master)
            print(f"GUI ERROR: Invalid SMTP port format for test email: {ve}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred while trying to send test email: {e}", parent=self.master)
            print(f"GUI ERROR: Unexpected error during send_test_email: {e}")


    def on_task_select(self, event=None): # event is ignored but passed by Tkinter bind
        """
        Handles selection changes in the tasks listbox.
        Updates the task details pane and enable/disable buttons.
        """
        selected_indices = self.tasks_listbox.curselection()
        if not selected_indices: # If nothing is selected
            self.clear_task_details()
            self.enable_task_button.config(state=tk.DISABLED)
            self.disable_task_button.config(state=tk.DISABLED)
            return

        selected_index = selected_indices[0]
        if 0 <= selected_index < len(self.tasks):
            selected_task_data = self.tasks[selected_index] # self.tasks is from config

            # Update details pane
            last_sent_str = "N/A"
            if selected_task_data.get("last_sent_time"):
                try:
                    from datetime import datetime 
                    dt_obj = datetime.fromisoformat(selected_task_data["last_sent_time"])
                    last_sent_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    last_sent_str = selected_task_data["last_sent_time"] 

            self.details_last_sent_var.set(f"Last Sent: {last_sent_str}")
            self.details_last_response_text.config(state=tk.NORMAL)
            self.details_last_response_text.delete("1.0", tk.END)
            self.details_last_response_text.insert(tk.END, selected_task_data.get("last_response", "No response recorded."))
            self.details_last_response_text.config(state=tk.DISABLED)

            # Update Enable/Disable buttons based on task's current 'enabled' state
            is_enabled = selected_task_data.get("enabled", True) # Default to True if not present
            if is_enabled:
                self.enable_task_button.config(state=tk.DISABLED)
                self.disable_task_button.config(state=tk.NORMAL)
            else:
                self.enable_task_button.config(state=tk.NORMAL)
                self.disable_task_button.config(state=tk.DISABLED)
        else:
            self.clear_task_details()
            self.enable_task_button.config(state=tk.DISABLED)
            self.disable_task_button.config(state=tk.DISABLED)

    def clear_task_details(self):
        """Clears the task details pane, resetting it to a default state."""
        self.details_last_sent_var.set("Last Sent: N/A")
        self.details_last_response_text.config(state=tk.NORMAL)
        self.details_last_response_text.delete("1.0", tk.END)
        self.details_last_response_text.insert(tk.END, "Select a task from the list to see its details.")
        self.details_last_response_text.config(state=tk.DISABLED)

    def _handle_task_enable_disable(self, enable_flag):
        """Common logic for enabling or disabling a selected task."""
        selected_indices = self.tasks_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select a task.")
            return

        selected_index = selected_indices[0]
        if 0 <= selected_index < len(self.tasks):
            task_to_modify = self.tasks[selected_index]
            task_id = task_to_modify.get("id")

            if not task_id:
                messagebox.showerror("Error", "Selected task has no ID. Cannot modify.")
                return

            # Create a copy to modify, then update
            updated_task_data = task_to_modify.copy()
            updated_task_data["enabled"] = enable_flag

            if config_manager.update_task_in_config(task_id, updated_task_data):
                # Refresh local tasks cache directly for consistency before UI update
                self.tasks = config_manager.get_tasks() 
                
                # Update listbox and selection state for buttons
                self.update_tasks_listbox() 
                # Try to reselect the item to update button states, may need index adjustment if list changes
                self.tasks_listbox.select_set(selected_index) 
                self.on_task_select() # Refresh button states based on new task state

                action = "enabled" if enable_flag else "disabled"
                messagebox.showinfo("Success", f"Task '{task_to_modify['prompt'][:30]}...' {action}.")

                # If scheduler is running, restart it to apply changes
                if scheduler._scheduler_thread and scheduler._scheduler_thread.is_alive():
                    print(f"GUI: Scheduler running, restarting to apply task enable/disable changes for task {task_id}")
                    self.stop_scheduler_gui()
                    self.start_scheduler_gui()
            else:
                messagebox.showerror("Error", f"Failed to update task '{task_to_modify['prompt'][:30]}...' state.")
        else:
            messagebox.showerror("Error", "Invalid task selection for enable/disable.")

    def enable_selected_task(self):
        """Enables the selected task."""
        self._handle_task_enable_disable(True)

    def disable_selected_task(self):
        """Disables the selected task."""
        self._handle_task_enable_disable(False)

    def periodic_update_tasks_display(self):
        """
        Periodically updates the task listbox (for countdowns) and the details pane
        (if a task is selected and its info might have changed).
        This function reschedules itself to run every second.
        """
        if scheduler._scheduler_thread and scheduler._scheduler_thread.is_alive():
            self.update_tasks_listbox() # Refreshes countdowns in the list
            # If a task is selected, its details (like last sent time/response) might change
            # due to scheduler actions, so refresh the details pane too.
            if self.tasks_listbox.curselection():
                self.on_task_select()
        self.master.after(1000, self.periodic_update_tasks_display) # Reschedule for the next second

    def stop_scheduler_gui(self, silent=False):
        print(f"DEBUG: gui.py -> stop_scheduler_gui(silent={silent}) CALLED") # DEBUG LOG
        scheduler.stop_scheduler_thread()
        if not silent:
            messagebox.showinfo("Scheduler", "Scheduler stopped.")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.add_task_button.config(state=tk.NORMAL)
        self.remove_task_button.config(state=tk.NORMAL)

    def open_smtp_settings_dialog(self):
        smtp_config = self.config.get("smtp_settings", config_manager.DEFAULT_CONFIG["smtp_settings"].copy())

        dialog = tk.Toplevel(self.master)
        dialog.title("SMTP Settings")
        dialog.transient(self.master) # Keep dialog on top of main window
        dialog.grab_set() # Modal behavior

        frame = ttk.Frame(dialog, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(frame, text="SMTP Server:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        server_var = tk.StringVar(value=smtp_config.get("server", ""))
        server_entry = ttk.Entry(frame, width=40, textvariable=server_var)
        server_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame, text="SMTP Port:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        port_var = tk.StringVar(value=str(smtp_config.get("port", "")))
        port_entry = ttk.Entry(frame, width=10, textvariable=port_var)
        port_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(frame, text="SMTP User:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        user_var = tk.StringVar(value=smtp_config.get("user", ""))
        user_entry = ttk.Entry(frame, width=40, textvariable=user_var)
        user_entry.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(frame, text="SMTP Password:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        password_var = tk.StringVar(value=smtp_config.get("password", ""))
        # TODO: Implement secure password storage instead of plaintext in config, as noted in config_manager.py.
        password_entry = ttk.Entry(frame, width=40, textvariable=password_var, show="*")
        password_entry.grid(row=3, column=1, padx=5, pady=5)

        use_tls_var = tk.BooleanVar(value=smtp_config.get("use_tls", True))
        tls_check = ttk.Checkbutton(frame, text="Use STARTTLS (e.g., for port 587)", variable=use_tls_var)
        tls_check.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        use_ssl_var = tk.BooleanVar(value=smtp_config.get("use_ssl", False))
        ssl_check = ttk.Checkbutton(frame, text="Use SSL directly (e.g., for port 465)", variable=use_ssl_var)
        ssl_check.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        # Logic to ensure only one can be selected if they are mutually exclusive
        # For now, EmailSender prioritizes SSL if both are true, which is a reasonable fallback.
        # A more interactive UI might disable one when the other is checked.

        def validate_port(P):
            if P == "":
                return True
            if P.isdigit() and 0 <= int(P) <= 65535:
                return True
            return False

        vcmd = (dialog.register(validate_port), '%P')
        port_entry.config(validate='key', validatecommand=vcmd)


        def on_save():
            try:
                port_val = port_var.get()
                if not port_val: # Default to 0 if empty, though server might reject. Or enforce entry.
                    messagebox.showerror("Error", "SMTP Port cannot be empty.", parent=dialog)
                    return

                port_num = int(port_val)
                if not (0 <= port_num <= 65535):
                    messagebox.showerror("Error", "Invalid port number. Must be between 0 and 65535.", parent=dialog)
                    return

                self.config["smtp_settings"]["server"] = server_var.get()
                self.config["smtp_settings"]["port"] = port_num
                self.config["smtp_settings"]["user"] = user_var.get()
                self.config["smtp_settings"]["password"] = password_var.get() # WARNING: Stored in plain text
                self.config["smtp_settings"]["use_tls"] = use_tls_var.get()
                self.config["smtp_settings"]["use_ssl"] = use_ssl_var.get()

                if use_ssl_var.get() and use_tls_var.get():
                    messagebox.showwarning("SMTP Setting Conflict", 
                                           "Both 'Use STARTTLS' and 'Use SSL directly' are selected.\n"
                                           "Direct SSL will be prioritized if both are enabled during sending.\n"
                                           "It's recommended to select only one.",
                                           parent=dialog)
                    # No need to return, just inform the user. EmailSender will handle it.

                if config_manager.save_config(self.config):
                    messagebox.showinfo("Success", "SMTP settings saved.", parent=dialog)
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "Failed to save SMTP settings.", parent=dialog)
            except ValueError:
                messagebox.showerror("Error", "Invalid port number. Please enter a valid number.", parent=dialog)
            except Exception as e:
                messagebox.showerror("Error", f"An unexpected error occurred: {e}", parent=dialog)

        def on_cancel():
            dialog.destroy()

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)

        save_button = ttk.Button(button_frame, text="Save", command=on_save)
        save_button.pack(side=tk.LEFT, padx=5)
        cancel_button = ttk.Button(button_frame, text="Cancel", command=on_cancel)
        cancel_button.pack(side=tk.LEFT, padx=5)

        # Center the dialog
        dialog.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        dialog.resizable(False, False)


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

        interval_value_str = self.interval_value_var.get().strip()
        interval_unit = self.interval_unit_var.get()
        search_internet = self.search_internet_var.get()

        if not interval_value_str.isdigit() or int(interval_value_str) <= 0:
            messagebox.showerror("Error", "Interval value must be a positive number.")
            return

        interval_value = int(interval_value_str)

        # Format interval string for scheduler.py (e.g., "5 minutes", "1 day")
        # Note: scheduler.py's _parse_interval will need to handle this format.
        # It expects "N unit(s)", so singular/plural might need adjustment or flexible parsing there.
        # For simplicity, using singular for now, assuming scheduler handles it or is adapted.
        # Example: "minutes" -> "minute" for "1 minute" vs "2 minutes"
        # The schedule library is flexible with plurals for its direct methods.

        # Map GUI display names to what 'schedule' library might expect or our parser.
        unit_mapping = {
            "Minutes": "minutes",
            "Hours": "hours",
            "Days": "days",
            "Weeks": "weeks"
        }
        parsed_unit = unit_mapping.get(interval_unit, "minutes") # Default to minutes if something is wrong

        interval_str = f"{interval_value} {parsed_unit}"
        
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
        # Interval check is implicitly handled by the new input method's structure
        # and the initial digit check.

        task_id = str(uuid.uuid4()) # Generate a unique ID for the task
        new_task = {
            "id": task_id,
            "prompt": prompt,
            "interval": interval_str, # Use the newly formatted interval string
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
            self.interval_value_var.set("1") # Reset to default
            self.interval_unit_combobox.set(self.interval_units[0]) # Reset to default
            self.search_internet_var.set(False)

            # If scheduler is running, restart it to include the new task
            if scheduler._scheduler_thread and scheduler._scheduler_thread.is_alive():
                print(f"GUI: Scheduler running, restarting to include new task {task_id}")
                self.stop_scheduler_gui(silent=True) # Stop silently
                self.start_scheduler_gui(silent=True) # Restart silently
                # Update button states as start/stop might change them
                self.start_button.config(state=tk.DISABLED)
                self.stop_button.config(state=tk.NORMAL)
                self.add_task_button.config(state=tk.DISABLED)
                self.remove_task_button.config(state=tk.DISABLED)


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
                         # scheduler.remove_task(task_id) # This is good, but a full restart is safer for consistency
                         print(f"GUI: Scheduler running, restarting after removing task {task_id}")
                         self.stop_scheduler_gui(silent=True)
                         self.start_scheduler_gui(silent=True)
                         # Update button states as start/stop might change them
                         self.start_button.config(state=tk.DISABLED)
                         self.stop_button.config(state=tk.NORMAL)
                         self.add_task_button.config(state=tk.DISABLED)
                         self.remove_task_button.config(state=tk.DISABLED)
                else:
                    messagebox.showerror("Error", "Failed to remove task from configuration.")
        else:
            messagebox.showerror("Error", "Invalid task selection.")


    def update_tasks_listbox(self):
        self.tasks_listbox.delete(0, tk.END)
        # self.tasks should be kept in sync with config_manager's tasks
        self.tasks = config_manager.get_tasks() # Refresh from source of truth config
        print(f"DEBUG: gui.py -> update_tasks_listbox -> self.tasks from config: {self.tasks}")
        
        # Get current statuses from the running scheduler if it's active
        scheduler_statuses = {}
        if scheduler._scheduler_thread and scheduler._scheduler_thread.is_alive():
            live_tasks_info = scheduler.list_tasks() # This now returns dicts with 'id' and 'time_remaining_str'
            for info in live_tasks_info:
                scheduler_statuses[info["id"]] = info["time_remaining_str"]
        print(f"DEBUG: gui.py -> update_tasks_listbox -> scheduler_statuses: {scheduler_statuses}")

        for i, task in enumerate(self.tasks):
            task_id = task.get("id", "NoID")
            status_icon = "✓" if task.get("enabled", True) else "✗"
            prompt_preview = task['prompt'][:30]
            interval_info = task['interval']

            countdown_str = ""
            if task.get("enabled", True): # Only show countdown for enabled tasks
                if task_id in scheduler_statuses:
                    countdown_str = f"(Next: {scheduler_statuses[task_id]})"
                elif scheduler._scheduler_thread and scheduler._scheduler_thread.is_alive():
                    # Task is enabled but not in live scheduler (e.g., just added, scheduler not refreshed yet)
                    countdown_str = "(Pending schedule)"
                else:
                    countdown_str = "(Scheduler stopped)"


            display_text = f"{status_icon} {task_id[:8]} | {prompt_preview}... | {interval_info} {countdown_str}"
            if task['search_internet']:
                display_text += " (Net)"
            self.tasks_listbox.insert(tk.END, display_text)

    def start_scheduler_gui(self, silent=False):
        self.save_main_config() # Save current API key and email before starting

        # Ensure self.tasks is up-to-date with the configuration file
        self.tasks = config_manager.get_tasks()
        print(f"DEBUG: gui.py -> start_scheduler_gui -> self.tasks reloaded: {self.tasks}")

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
        print(f"DEBUG: gui.py -> start_scheduler_gui -> Called scheduler.start_scheduler_thread with active_tasks: {active_tasks}")
        if not silent:
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
        print("DEBUG: gui.py -> on_closing() CALLED") # DEBUG LOG
        if messagebox.askokcancel("Quit", "Do you want to quit?\nThis will stop the scheduler if it's running."):
            print("DEBUG: gui.py -> on_closing() - User chose to quit.") # DEBUG LOG
            self.save_main_config() # Save any changes in API key/email
            if scheduler._scheduler_thread and scheduler._scheduler_thread.is_alive():
                print("DEBUG: gui.py -> on_closing() is calling stop_scheduler_gui()") # DEBUG LOG
                self.stop_scheduler_gui()
            self.master.destroy()
        else:
            print("DEBUG: gui.py -> on_closing() - User cancelled quit.") # DEBUG LOG


if __name__ == '__main__':
    # This is for testing the GUI in isolation.
    # Real application uses main.py
    root = tk.Tk()
    app = App(root)
    root.mainloop()
