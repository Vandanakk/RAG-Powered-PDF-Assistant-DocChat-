import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key or api_key.startswith("your_gemini_api_key"):
    print("❌ GEMINI_API_KEY not set. Please add a valid key to your .env file.")
else:
    client = genai.Client(api_key=api_key)
    print("Sending request to Gemini...")
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents='Tell me one interesting fact about space engineering in 15 words or less.',
        )
        print("\n--- GEMINI RESPONSE ---")
        print(response.text)
    except Exception as e:
        print(f"❌ Error communicating with Gemini API: {e}")