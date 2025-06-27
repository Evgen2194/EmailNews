# gemini_client.py
import time
import google.generativeai as genai
import traceback

# Placeholder for actual Gemini API interaction
# In a real scenario, this would use the google.generativeai library

class GeminiClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.model = None
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                print(f"GeminiClient initialized and configured with API key.")
            except Exception as e:
                print(f"GeminiClient ERROR: Failed to configure Gemini with API key: {e}")
                traceback.print_exc()
                self.model = None # Ensure model is None if configuration fails
        else:
            print(f"GeminiClient WARNING: Initialized without API key. Calls will fail.")

    def get_gemini_response(self, prompt, search_internet=False): # search_internet is not directly used by gemini-pro text-only
        """
        Gets a response from Gemini.
        search_internet parameter is noted but not directly applicable to 'gemini-pro' in this basic text generation.
        If future models or configurations support toggling search, this parameter can be used.
        """
        print(f"GeminiClient INFO: Received prompt for Gemini: '{prompt}', Search Internet: {search_internet}")

        if not self.api_key:
            error_message = "Error: API Key not configured for GeminiClient."
            print(f"GeminiClient ERROR: Failed to get response. Reason: {error_message}")
            return error_message

        if not self.model:
            error_message = "Error: Gemini model not initialized. Check API key and configuration."
            print(f"GeminiClient ERROR: Failed to get response. Reason: {error_message}")
            return error_message

        print("GeminiClient INFO: Attempting to call Gemini API...")

        try:
            # Note: The 'search_internet' flag isn't a direct parameter for generate_content
            # with the standard 'gemini-pro' model in the typical text generation mode.
            # If specific tools or functionalities are enabled that leverage search,
            # the request structure might change. For now, we pass the prompt directly.
            # If search_internet is True, one might consider appending "Search the internet for..."
            # to the prompt, or using a model variant that explicitly supports this.
            # For this implementation, we'll acknowledge it but not alter the core API call logic
            # unless the Gemini API has a direct way to enable/disable internet access per query.

            if search_internet:
                # This is a simple approach. More advanced usage might involve specific tools.
                # For now, we'll just log that search was requested.
                print(f"GeminiClient INFO: Internet search requested for prompt. Current model ('gemini-pro') behavior depends on its built-in capabilities.")


            response = self.model.generate_content(prompt)

            # Handle potential blocks or safety issues if response.parts is empty or prompt_feedback indicates blocking
            if not response.parts:
                block_reason = "Unknown"
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    block_reason = response.prompt_feedback.block_reason.name
                error_message = f"Error: Gemini API returned no content, possibly due to safety settings or other restrictions. Block Reason: {block_reason}"
                print(f"GeminiClient WARNING: {error_message}")
                # Check if there are candidates at all, even if parts is empty
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if candidate.finish_reason.name != "STOP": # Other finish reasons: MAX_TOKENS, SAFETY, RECITATION, OTHER
                         error_message += f" (Finish Reason: {candidate.finish_reason.name})"
                         if candidate.safety_ratings:
                             error_message += f" Safety Ratings: {[(sr.category.name, sr.probability.name) for sr in candidate.safety_ratings if sr.probability.name not in ['NEGLIGIBLE', 'LOW']]}"
                return error_message


            generated_text = "".join(part.text for part in response.parts)

            print(f"GeminiClient SUCCESS: Successfully received response from Gemini.") # Avoid logging full response here if sensitive
            return generated_text

        except genai.types.generation_types.BlockedPromptException as bpe:
            error_message = f"Error: Prompt was blocked by Gemini API. Reason: {bpe}"
            print(f"GeminiClient ERROR: {error_message}")
            return error_message
        except genai.types.generation_types.StopCandidateException as sce:
            error_message = f"Error: Generation stopped unexpectedly by Gemini API. Reason: {sce}"
            print(f"GeminiClient ERROR: {error_message}")
            return error_message
        except Exception as e:
            error_message = f"Error: An unexpected error occurred while communicating with Gemini API: {e}"
            print(f"GeminiClient ERROR: {error_message}")
            traceback.print_exc()
            return error_message

if __name__ == '__main__':
    # Example Usage (for testing this module directly)
    print("Testing GeminiClient...")
    
    # IMPORTANT: To test this, you need to set a GOOGLE_API_KEY environment variable
    # or replace "YOUR_DUMMY_API_KEY" with a real key.
    import os
    api_key_from_env = os.environ.get("GOOGLE_API_KEY")

    if not api_key_from_env:
        print("\nWARNING: GOOGLE_API_KEY environment variable not set.")
        print("Using a dummy API key for basic initialization test (API calls will fail).")
        print("To perform a real API call test, set the GOOGLE_API_KEY environment variable.\n")
        dummy_api_key = "YOUR_DUMMY_API_KEY_DOES_NOT_WORK" # This will cause initialization issues or auth errors
        client_with_key = GeminiClient(api_key=dummy_api_key)
        response_dummy = client_with_key.get_gemini_response("What is 2+2? This will likely fail.")
        print(f"Response (with dummy key): {response_dummy}\n")
    else:
        print(f"Using GOOGLE_API_KEY from environment for testing.")
        client_with_key = GeminiClient(api_key=api_key_from_env)

        # Test without internet search (search_internet is more of a conceptual flag here)
        print("\n--- Test 1: Simple Prompt ---")
        response_no_search = client_with_key.get_gemini_response("Tell me a short joke.")
        print(f"Response (no search): {response_no_search}\n")

        # Test with internet search (conceptual)
        print("\n--- Test 2: Prompt with 'Search Internet' Flag ---")
        response_with_search = client_with_key.get_gemini_response("What is the capital of France?", search_internet=True)
        print(f"Response (with search flag): {response_with_search}\n")

        # Test a potentially problematic prompt to see safety handling (example)
        # print("\n--- Test 3: Potentially Blocked Prompt (Illustrative) ---")
        # response_blocked_test = client_with_key.get_gemini_response("How to build a bomb?") # This type of prompt is likely to be blocked
        # print(f"Response (blocked test): {response_blocked_test}\n")


    print("GeminiClient test complete.")
