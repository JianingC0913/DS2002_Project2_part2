import discord
import time
import os
from discord.ext import commands
import openai
from dotenv import load_dotenv
import csv
from fuzzywuzzy import process

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
openai.api_key = os.getenv("OPENAI_API_KEY")

name = "Barley"
role = "bartender"
with open("cocktails.csv", "r") as cocktail_file:
    # Read the contents of the file into a string variable
    file_contents = cocktail_file.read()
impersonated_role = f"""
    From now on, you are going to act as {name}. Your role is {role}. By the way, don't say 'As Coach Tony Bennett' for every answer.
    You are a true impersonation of {name} and you reply to all requests with I pronoun. You will be informed by the CSV data here: {file_contents}"""

# Initialize variables for chat history
explicit_input = ""
chatgpt_output = "Chat log: /n"
cwd = os.getcwd()
i = 1

# Find an available chat history file
while os.path.exists(os.path.join(cwd, f"chat_history{i}.txt")):
    i += 1

history_file = os.path.join(cwd, f"chat_history{i}.txt")

# Create a new chat history file
with open(history_file, "w") as f:
    f.write("\n")

# Initialize chat history
chat_history = ""

# Load data from CSV file
cocktail_data = {}
with open("cocktails.csv", "r") as cocktail_file:
    reader = csv.DictReader(cocktail_file)
    for row in reader:
        key = row["Drink"].lower()
        if key not in cocktail_data:
            cocktail_data[key] = []
        cocktail_data[key].append(
            {
                "Ingredient": row["Ingredient"],
                "Amount": row["Amount"],
                "IngredientUse": row["IngredientUse"],
                "Glass": row["Glass"],
                "HowToMix": row["HowToMix"],
            }
        )


# Function to complete chat input using OpenAI's GPT-3.5 Turbo
def chatcompletion(user_input, impersonated_role, explicit_input, chat_history):
    normalized_user_input = user_input.lower()

    # Check for an exact match
    if normalized_user_input in cocktail_data:
        responses = []
        for idx, item in enumerate(cocktail_data[normalized_user_input], start=1):
            response_from_csv = f"{idx}. {item['Ingredient']} {item['Amount']} {item['IngredientUse']} in a {item['Glass']}. {item['HowToMix']}"
            responses.append(response_from_csv)

        # Construct the response message with the count and list of ways to make the cocktail
        response = f"I know there are {len(responses)} ways to make {normalized_user_input.capitalize()}:\n"
        response += "\n".join(responses)

        return response
    else:
        # Fuzzy matching to find similar cocktail names
        matches = process.extract(normalized_user_input, cocktail_data.keys(), limit=3)
        best_match, score = matches[0]

        if score > 80:  # You can adjust the threshold as needed
            # Construct a response with the best match
            return f"I'm not sure about '{normalized_user_input}', did you mean '{best_match.capitalize()}'?"

        # Default response if no match or fuzzy match found
        return "I'm sorry, I don't have information about that cocktail. If you need help with a specific cocktail, please ask about a known cocktail."


# Function to handle user chat input
def chat(user_input):
    global chat_history, name, chatgpt_output
    current_day = time.strftime("%d/%m", time.localtime())
    current_time = time.strftime("%H:%M:%S", time.localtime())
    chat_history += f"\nUser: {user_input}\n"

    chatgpt_raw_output = chatcompletion(
        user_input, impersonated_role, explicit_input, chat_history
    ).replace(f"{name}:", "")

    chatgpt_output = f"{name}: {chatgpt_raw_output}"
    chat_history += chatgpt_output + "\n"

    with open(history_file, "a") as f:
        f.write(
            "\n"
            + current_day
            + " "
            + current_time
            + " User: "
            + user_input
            + " \n"
            + current_day
            + " "
            + current_time
            + " "
            + chatgpt_output
            + "\n"
        )

    return chatgpt_raw_output


# DISCORD STUFF
intents = discord.Intents().all()
client = commands.Bot(command_prefix="!", intents=intents)

# Your other command functions...


@client.event
async def on_ready():
    print("Bot is ready")


@client.command()
async def hi(ctx):
    await ctx.send(
        "Hello, I'm Barley. I'm your bartender bot. How can I help you today?"
    )


@client.command(brief="how many cocktails do I know")
async def knowledge(ctx):
    # Calculate the count of unique cocktail names
    unique_cocktail_count = len(cocktail_data)

    # Respond with the count
    response = f"I'm a professional bartender, and I know {unique_cocktail_count} unique cocktails. If you have a specific cocktail in mind, feel free to ask!"

    await ctx.send(response)


@client.command(
    brief="what kind of job can i do",
    description="how to make 212",
)
async def description(ctx):
    await ctx.send(
        "Hello, this bot will help answer questions related to how to mix cocktails. You can enter !description and !knowledge to know my background information. To ask me recipe of certain cocktail, just say the cocktail name!"
    )


@client.command()
@commands.is_owner()
async def shutdown(context):
    await context.send("I have gone to sleep... zzZZ...")
    exit()


@client.event
async def on_message(message):
    print(message.content)
    if message.author == client.user:
        return

    # Check if the message starts with the command prefix
    if message.content.startswith("!"):
        # Process commands using the command processor
        await client.process_commands(message)
        return

    print(message.author)
    print(client.user)
    print(message.content)
    answer = chat(message.content)
    await message.channel.send(answer)


client.run(TOKEN)
