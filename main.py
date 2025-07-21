import pandas as pd
import google.generativeai as genai
import os
import time
from google.api_core.exceptions import ResourceExhausted, InternalServerError, Aborted, TooManyRequests, ServiceUnavailable


# --- IMPORTANT: FOR ASSESSMENT ONLY, NOT RECOMMENDED FOR PRODUCTION CODE ---
# Assign your actual API key directly here.
# Replace 'YOUR_ACTUAL_GOOGLE_API_KEY_GOES_HERE' with the key you got from Google AI Studio.
API_KEY = "AIzaSyC2f7RlRMku4josPAU9v8sVynhc5Uv9vIU"
# --------------------------------------------------------------------------

# Configure the Google AI Studio API with your key
if not API_KEY or API_KEY == "YOUR_ACTUAL_GOOGLE_API_KEY_GOES_HERE":
    raise ValueError("API Key is missing or still a placeholder. Please replace it with your actual key.")

genai.configure(api_key=API_KEY)

# print("Listing available models that support 'generateContent':")
# for m in genai.list_models():
#     if 'generateContent' in m.supported_generation_methods:
#         print(m.name)

# Initialize the Generative Model (you might use 'gemini-pro' or other available models)
model = genai.GenerativeModel('gemini-2.0-flash-lite')

# Load your CSV data
try:
    df = pd.read_csv('Game Thumbnail.csv')
    print("Data loaded successfully. First 5 rows:")
    print(df.head())
except FileNotFoundError:
    print("Error: 'Game Thumbnail.csv' not found. Make sure the file is in the same directory as your script.")
    exit()

# Add new empty columns to store the results
df['genre'] = ''
df['short_description'] = ''
df['player_mode'] = ''

# Function to make an API call and handle potential errors
def get_ai_response(prompt_template, game_title, max_retries=5, initial_delay=1, max_delay=60):
    """
    Makes an API call to the Generative AI model, with retry logic for transient errors and quota issues.

    Args:
        prompt_template (str): The prompt string with a placeholder for game_title.
        game_title (str): The title of the game to query.
        max_retries (int): Maximum number of retries for an API call.
        initial_delay (int): Initial delay in seconds before the first retry.
        max_delay (int): Maximum delay in seconds between retries (for exponential backoff).

    Returns:
        str: The AI's response text, 'N/A' if no valid content, 'Error' for general failures,
             or 'QuotaError' if persistent quota issues occur.
    """
    prompt = prompt_template.format(game_title=game_title)
    current_delay = initial_delay

    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            if response and response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text.strip()
            else:
                print(f"Warning: No valid content in response for '{game_title}' after AI call. Prompt: {prompt}")
                return "N/A"
        except (ResourceExhausted, TooManyRequests) as e:
            # This handles 429 errors (Quota Exceeded)
            print(f"Quota exceeded for '{game_title}' (Attempt {attempt + 1}/{max_retries}): {e}")
            print(f"Waiting for {current_delay} seconds before retrying due to quota...")
            time.sleep(current_delay)
            current_delay = min(current_delay * 2, max_delay) # Exponential backoff
        except (InternalServerError, ServiceUnavailable, Aborted) as e:
            # Handles other common transient API errors (e.g., 500s, 503s)
            print(f"Transient API error for '{game_title}' (Attempt {attempt + 1}/{max_retries}): {e}")
            print(f"Waiting for {current_delay} seconds before retrying...")
            time.sleep(current_delay)
            current_delay = min(current_delay * 2, max_delay) # Exponential backoff
        except Exception as e:
            # Catches any other unexpected errors during the API call
            print(f"Unexpected API call error for '{game_title}' (Attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Waiting for {current_delay} seconds before retrying...")
                time.sleep(current_delay)
                current_delay = min(current_delay * 2, max_delay)
            else:
                print(f"Failed after {max_retries} attempts for '{game_title}' due to unexpected error.")
                return "Error" # Return a general error placeholder

    # If all retries are exhausted for quota/transient issues
    print(f"Failed after {max_retries} attempts for '{game_title}' due to persistent API errors. Consider increasing delays, checking billing, or pausing the script.")
    return "QuotaError" # Indicate persistent quota failure

# Define your prompts
genre_prompt = '''"Classify the primary genre of the game '{game_title}' in a single word. 
If multiple genres apply, choose the most prominent one. Response should be only the genre word."'''

description_prompt = '''"Write a short, engaging description for the game '{game_title}', 
under 30 words. Focus on its core concept."'''

player_mode_prompt = '''"Identify the primary player mode for the game '{game_title}'. 
Respond only with 'Singleplayer', 'Multiplayer', or 'Both'."'''


# Iterate through the DataFrame and make API calls
for index, row in df.iterrows():
    game_title = row['game_title']
    print(f"Processing: {game_title} (Row {index+1}/{len(df)})")

    # Get Genre
    genre = get_ai_response(genre_prompt, game_title)
    df.at[index, 'genre'] = genre

    # Get Short Description
    description = get_ai_response(description_prompt, game_title)
    df.at[index, 'short_description'] = description

    # Get Player Mode
    player_mode = get_ai_response(player_mode_prompt, game_title)
    df.at[index, 'player_mode'] = player_mode

    # Optional: Add a small delay between requests to avoid hitting rate limits
    time.sleep(2) # Adjust as needed

print("\nProcessing complete. Enhanced DataFrame head:")
print(df.head())

# Save the enhanced DataFrame to a new CSV file
output_filename = 'Enhanced_Game_Thumbnails.csv'
df.to_csv(output_filename, index=False)
print(f"\nEnhanced data saved to {output_filename}")