import openai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
NINJA_API_KEY = os.getenv('NINJA_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Configure OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

def test_openai_connection():
    """Test OpenAI API connection"""
    try:
        print("Testing OpenAI connection...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello, test successful!'"}
            ],
            max_tokens=20
        )
        print("Response:", response.choices[0].message.content)
        return True
    except Exception as e:
        print("OpenAI Error:", str(e))
        return False

def main():
    # Step 1: Check environment variables
    print("\nStep 1: Checking environment variables")
    print(f"OPENAI_API_KEY present: {'Yes' if OPENAI_API_KEY else 'No'}")
    print(f"NINJA_API_KEY present: {'Yes' if NINJA_API_KEY else 'No'}")

    # Step 2: Test OpenAI connection
    print("\nStep 2: Testing OpenAI connection")
    if test_openai_connection():
        print("OpenAI connection successful!")
    else:
        print("OpenAI connection failed!")

if __name__ == "__main__":
    main()