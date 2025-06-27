# email_sender.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailSender:
    def __init__(self, smtp_server, smtp_port, smtp_user, smtp_password, use_tls=True, use_ssl=False):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password # Should be handled securely
        self.use_tls = use_tls # For STARTTLS
        self.use_ssl = use_ssl # For direct SSL connection

        if self.use_ssl and self.use_tls:
            # It's generally one or the other. Direct SSL implies TLS from the start.
            # STARTTLS upgrades a plain connection. For clarity, ensure only one is primary.
            # We'll prioritize direct SSL if both are somehow true.
            print(f"EmailSender WARNING: Both use_ssl and use_tls are True. Prioritizing direct SSL.")
            self.use_tls = False # Disable STARTTLS if direct SSL is active

        security_mode = "Direct SSL" if self.use_ssl else ("STARTTLS" if self.use_tls else "None")
        print(f"EmailSender initialized for {smtp_user}@{smtp_server}:{smtp_port} (Security: {security_mode})")

    def send_email(self, to_email, subject, body_html, body_text=None):
        """
        Sends an email.
        to_email: Recipient's email address.
        subject: Subject of the email.
        body_html: HTML content of the email.
        body_text: Plain text version of the email (optional, good for compatibility).
        """
        if not all([self.smtp_server, self.smtp_port, self.smtp_user, self.smtp_password]):
            print("EmailSender Error: SMTP configuration is incomplete. Cannot send email.")
            # In a real app, this might raise an error or return a specific status
            return False

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.smtp_user
        msg['To'] = to_email

        if body_text:
            part_text = MIMEText(body_text, 'plain')
            msg.attach(part_text)
        
        if body_html:
            part_html = MIMEText(body_html, 'html')
            msg.attach(part_html)
        elif not body_text: # Must have at least one body part
             print("EmailSender Error: Email body (HTML or text) is required.")
             return False


        try:
            connection_details = f"{self.smtp_server}:{self.smtp_port}"
            server = None # Initialize server variable

            if self.use_ssl:
                print(f"EmailSender: Attempting SSL connection to {connection_details}")
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                print(f"EmailSender: Attempting non-SSL connection to {connection_details}")
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                if self.use_tls:
                    print(f"EmailSender: Securing connection with STARTTLS for {connection_details}")
                    server.starttls() # Secure the connection

            # Login and send regardless of connection type (SSL or STARTTLS)
            # No need for 'with' statement if we manually quit, or ensure it's handled.
            # For simplicity, let's ensure server.quit() is called in a finally block or rely on 'with' if possible.
            # The 'with' statement is cleaner if SMTP_SSL also supports it directly.
            # SMTP_SSL objects don't need starttls(). They are secure from the start.

            # Re-evaluating the 'with' block:
            # smtplib.SMTP and smtplib.SMTP_SSL can both be used as context managers.

            if self.use_ssl:
                print(f"EmailSender: Establishing SMTP_SSL session with {connection_details}")
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server_ssl:
                    # No server.starttls() here as it's SSL from the start
                    server_ssl.login(self.smtp_user, self.smtp_password)
                    server_ssl.sendmail(self.smtp_user, to_email, msg.as_string())
            else: # Standard SMTP, possibly with STARTTLS
                print(f"EmailSender: Establishing SMTP session with {connection_details}")
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server_std:
                    if self.use_tls:
                        print(f"EmailSender: Upgrading to STARTTLS for {connection_details}")
                        server_std.starttls()
                    server_std.login(self.smtp_user, self.smtp_password)
                    server_std.sendmail(self.smtp_user, to_email, msg.as_string())

            print(f"EmailSender SUCCESS: Email sent successfully to {to_email} with subject '{subject}'")
            return True

        except smtplib.SMTPAuthenticationError as e:
            print(f"EmailSender ERROR: SMTP Authentication failed for user {self.smtp_user}. Check credentials. Error: {e}")
        except smtplib.SMTPServerDisconnected as e:
            print(f"EmailSender ERROR: SMTP server disconnected. Check server address/port or network. Error: {e}")
        except smtplib.SMTPConnectError as e:
            print(f"EmailSender ERROR: Could not connect to SMTP server {self.smtp_server}:{self.smtp_port}. Error: {e}")
        except ConnectionRefusedError as e: # More specific than just SMTPConnectError for some cases
            print(f"EmailSender ERROR: Connection refused by server {self.smtp_server}:{self.smtp_port}. Check firewall or if server is running. Error: {e}")
        except OSError as e: # Catches errors like [Errno 11001] getaddrinfo failed
             print(f"EmailSender ERROR: OS error while connecting to {self.smtp_server}:{self.smtp_port}. Could be DNS issue or network problem. Error: {e}")
        except Exception as e:
            print(f"EmailSender ERROR: An unexpected error occurred while sending email: {type(e).__name__} - {e}")
        return False

if __name__ == '__main__':
    print("Testing EmailSender...")
    
    # --- IMPORTANT ---
    # For this test to work, you need to provide REAL SMTP credentials and a recipient.
    # Using a service like Gmail requires "Less Secure App Access" to be enabled
    # or an "App Password" to be generated.
    # DO NOT COMMIT REAL CREDENTIALS TO VERSION CONTROL.
    # Consider using environment variables or a local config file for testing.

    # Example using environment variables (recommended for local testing):
    # import os
    # SMTP_SERVER = os.environ.get("TEST_SMTP_SERVER") # e.g., "smtp.gmail.com"
    # SMTP_PORT = int(os.environ.get("TEST_SMTP_PORT", 587)) # e.g., 587 for TLS
    # SMTP_USER = os.environ.get("TEST_SMTP_USER")     # e.g., "your.email@gmail.com"
    # SMTP_PASSWORD = os.environ.get("TEST_SMTP_PASSWORD") # e.g., "your_app_password"
    # TEST_RECIPIENT_EMAIL = os.environ.get("TEST_RECIPIENT_EMAIL")

    # --- Placeholder credentials (WILL NOT WORK) ---
    SMTP_SERVER = "smtp.example.com"
    SMTP_PORT = 587
    SMTP_USER = "user@example.com"
    SMTP_PASSWORD = "password"
    TEST_RECIPIENT_EMAIL = "recipient@example.com"
    USE_TLS = True # Common for port 587

    print("\n--- Configuration ---")
    print(f"Server: {SMTP_SERVER}, Port: {SMTP_PORT}, User: {SMTP_USER}, TLS: {USE_TLS}")
    print(f"Test Recipient: {TEST_RECIPIENT_EMAIL}")
    print("Note: For actual sending, replace placeholder credentials with real ones.")
    print("You might need to set environment variables or edit the script directly (not recommended for sensitive data).")


    if SMTP_SERVER == "smtp.example.com":
        print("\nSkipping actual email sending test as placeholder credentials are used.")
        print("To run a real test, update SMTP settings in the __main__ block of email_sender.py.")
    else:
        sender = EmailSender(
            smtp_server=SMTP_SERVER,
            smtp_port=SMTP_PORT,
            smtp_user=SMTP_USER,
            smtp_password=SMTP_PASSWORD,
            use_tls=USE_TLS
        )

        test_subject = "Test Email from EmailSender"
        test_body_html = """
        <html>
        <body>
            <h1>Hello from EmailSender!</h1>
            <p>This is a <b>test email</b> sent via the EmailSender class.</p>
            <p>If you are seeing this, it means the HTML part of the email is working.</p>
        </body>
        </html>
        """
        test_body_text = """
        Hello from EmailSender!
        This is a test email sent via the EmailSender class.
        If you are seeing this, it means the plain text part of the email is working.
        """

        print(f"\nAttempting to send test email to {TEST_RECIPIENT_EMAIL}...")
        success = sender.send_email(TEST_RECIPIENT_EMAIL, test_subject, test_body_html, test_body_text)

        if success:
            print("Test email sent. Please check the recipient's inbox (and spam folder).")
        else:
            print("Failed to send test email. Check console output for errors.")

    print("\nEmailSender test complete.")
