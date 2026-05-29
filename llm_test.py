from google import genai
client = genai.Client(api_key="AIzaSyAQvxk5dCTKMx7KWsXePy2_lpWRCh9pYNY")

print("Sending request to Gemini...")

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Tell me one interesting fact about space engineering in 15 words or less.',
)

print("\n--- GEMINI RESPONSE ---")
print(response.text)