import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

def complete_command(current_input, previous_commands):
    # Configure with your Gemini API 
    genai.configure(api_key="AIzaSyAAD3DIlgG-9u343AY7CJvQTyQVY-tLKFM") 

    # Load Gemini model
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Prompt to complete the command based on context
    prompt = f"""You are an assistant that completes partial user commands based on past full commands.

Past commands:
{chr(10).join(f"- {cmd}" for cmd in previous_commands)}

Current input: "{current_input}"
Using the most relevant past command(s), complete the current input.

Respond only with the completed command.
"""

    # Generate response
    response = model.generate_content(prompt)
    return response.text.strip()


# run  the code
if __name__ == "__main__":
    previous_commands = [
        "open the door",
        "switch off light l1",
        "lock the main gate"
    ]
    current_input = input("Enter the current command: ")

    completed_command = complete_command(current_input, previous_commands)
    print("Completed Command:", completed_command)
