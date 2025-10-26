from gemini_api import generate_response
import time

def test_api_connection():
    """Test Gemini response outside Streamlit."""
    print("--- Testing Gemini API ---")
    prompt = "What are the three most popular pet names?"
    response = generate_response(prompt)
    print("\nPrompt:", prompt)
    print("\nResponse:", response)
    print("\n--- Test Complete ---")

if __name__ == "__main__":
    time.sleep(1)
    test_api_connection()
