#!/usr/bin/env python3

# rbot.py - https://github.com/rajivpant/rbot
# Developed by Rajiv Pant (https://github.com/rajivpant)
# The first version was inspired by 
# - Jim Mortko (https://github.com/jskills)
# - Alexandria Redmon (https://github.com/alexdredmon)
#
# 🤖 rbot: Rajiv's AI augmented brain, assistant, and chatbot
# utilizing OpenAI's GPT and Anthropic's Claude models 
# to offer engaging conversations
# with a personalized touch and advanced context understanding.
#
# 🚀 Rajiv's GPT-4 based chatbot processes user prompts and custom conversation decorators,
# enabling more context-aware responses than out-of-the-box ChatGPT Plus with GPT-4.
#
# Custom decorators are a simpler way to achieve outcomes similar to those of
# Parameter-Efficient Fine-Tuning (PEFT) methods.
# 
# 🧠 Custom conversation decorators help the chatbot better understand the context,
# resulting in more accurate and relevant responses, surpassing the capabilities of
# out of the box GPT-4 implementations.


import glob
import os
import sys
from dotenv import load_dotenv
import argparse
import re
import yaml
import json
import appdirs
import openai
import anthropic
from helpers import load_decorator_files, load_config, print_saved_files


appname = "rbot"
appauthor = "Rajiv Pant"

data_dir = appdirs.user_data_dir(appname, appauthor)
sessions_data_dir = os.path.join(data_dir, "sessions")



load_dotenv()  # Load environment variables from .env file


# Load configuration from engines.yaml
config = load_config('engines.yaml')
engines_config = {engine['name']: engine for engine in config['engines']}
engine_choices = list(engines_config.keys())



def chat(
    prompt,
    decorators,
    model,
    max_tokens=1000,
    stream=True,
    request_timeout=15,
    temperature=0.75,
    history=None,
    engine="openai",
):
    """
    Send a request to the OpenAI or Anthropic API with the provided prompt and decorators.

    :param prompt: The user's input to generate a response for.
    :param decorators: A list of decorators to provide context for the model.
    :param model: The name of the GPT model to use.
    :param max_tokens: The maximum number of tokens to generate in the response (default is 1000).
    :param stream: Whether to stream the response from the API (default is True).
    :param request_timeout: The request timeout in seconds (default is 15).
    :param temperature: The creativity of the response, with higher values being more creative (default is 0.75).
    :param history: The conversation history, if available (default is None).
    :param engine: The engine to use for the chat, 'openai' or 'anthropic' (default is 'openai').
    :return: The generated response text from the model.
    """
    if engine == "openai":
        # Configure the arguments for the OpenAI API
        args = {
            "max_tokens": max_tokens,
            "model": model,
            "request_timeout": request_timeout,
            "stream": stream,
            "temperature": temperature,
        }
        # If conversation history is provided, pass it to the API
        if history:
            args["messages"] = history
        else:
            # If no history is provided, construct it from the decorators
            history = []
            for decorator in decorators:
                history.append(
                    {
                        "role": "system",
                        "content": decorator,
                    }
                )
            # Add the user's prompt to the history
            history.append({"role": "user", "content": prompt})
            args["messages"] = history

        # Call the OpenAI API and build the response
        completion_method = openai.ChatCompletion.create
        response = ""
        for token in completion_method(**args):
            text = token["choices"][0]["delta"].get("content")
            if text:
                response += text
        return response
    elif engine == "anthropic":
        # Call the Anthropic API
        c = anthropic.Client(anthropic.api_key)
        resp = c.completion(
            prompt=f"{anthropic.HUMAN_PROMPT} {prompt} {anthropic.AI_PROMPT}",
            stop_sequences=[anthropic.HUMAN_PROMPT],
            model=model,
            max_tokens_to_sample=max_tokens,
        )
        return resp['completion']





def main():
    parser = argparse.ArgumentParser(
        description="A GPT-4 or Anthropic Claude based chatbot that generates responses based on user prompts."
    )
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "-ls",
        "--list-saved",
        action="store_true",
        help="List all the currently saved JSON files."
    )
    input_group2 = parser.add_mutually_exclusive_group()
    input_group2.add_argument(
        "-p", "--prompt", help="The user's input to generate a response for."
    )
    input_group2.add_argument(
        "-f",
        "--prompt_file",
        help="The file containing the user's input to generate a response for.",
    )
    input_group2.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Enable interactive assistant chatbot mode.",
    )
    input_group2.add_argument(
        "--stdin",
        action="store_true",
        help="Read the user's input from stdin."
    )
    parser.add_argument(
        "-d", "--decorator", nargs='*', default=[],
        help="Path to the conversation decorator file or folder. Can accept multiple values."
    )
    parser.add_argument(
        "-l",
        "--load",
        help="Load a previous session from a file.",
    )
    parser.add_argument(
        "-e",
        "--engine",
        default=config.get('default', 'openai'),
        choices=engine_choices,
        help="The engine to use for the chat.",
    )
    parser.add_argument(
        "-m",
        "--model",
        help="The model to use for the chat. Defaults to engine's default model.",
    )
    parser.add_argument(
        "-t",
        "--temperature",
        type=float,
        default=0.75,
        help="The creativity of the response, with higher values being more creative (default is 0.75).",
    )
    parser.add_argument(
        "-nd", "--nodecorator",
        action="store_true",
        help="Ignore all decorators even if they are specified."
    )

    known_args = parser.parse_known_args()
    args = known_args[0]

    if args.list_saved:
        print_saved_files(data_dir)
        return

    if args.load:
        args.interactive = True  # Automatically enable interactive mode when loading a session
        args.nodecorator = True  # Do not load decorator files when loading a session

    decorators = []
    decorator_files = []  # to store file names of decorators

    if not args.nodecorator:
        # Load default decorators from .env file
        default_decorator_paths = os.getenv("DECORATORS", "").split("\n")
        default_decorator_paths = [path for path in default_decorator_paths if path.strip() != '']
        decorators, decorator_files = load_decorator_files(default_decorator_paths + args.decorator)

    if decorator_files:
        print("Decorators being used:")
        for file in decorator_files:
            print(f" - {file}")
    else:
        print("No decorator files are being used.")

    history = []
    for decorator in decorators:
        history.append(
            {
                "role": "system",
                "content": decorator,
            }
        )
    if args.load:
        filename = args.load.strip()  # Remove leading and trailing spaces
        full_path = os.path.join(sessions_data_dir, filename)
        with open(full_path, 'r') as f:
            history = json.load(f)

    model = args.model
    if model is None:
        model = engines_config[args.engine]['default_model']

    # Get the engine API key from environment variable
    api_key_name = engines_config[args.engine].get('api_key_name')
    if api_key_name:
        engines_config[args.engine]['api_key'] = os.getenv(api_key_name)

    if args.engine == 'openai':
        openai.api_key = engines_config[args.engine]['api_key']
    elif args.engine == 'anthropic':
        anthropic.api_key = engines_config[args.engine]['api_key']

    print(f"Using AI engine {args.engine} with model {model}")
    print(f"Creativity temperature setting: {args.temperature}")

    if args.interactive:
        print("Entering interactive mode.")
        while True:
            prompt = input("\nEnter prompt below. /quit to exit or /save file_name.json to save conversation.\n> ")
            if prompt.lower() == "/quit":
                break
            elif prompt.lower().startswith("/save "):
                filename = prompt[6:].strip()  # Remove leading '/save ' and spaces
                full_path = os.path.join(sessions_data_dir, filename)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f:
                    json.dump(history, f)
                print(f"Conversation saved to {full_path}")
                continue
            history.append({"role": "user", "content": prompt})
            reply = chat(prompt=prompt, decorators=decorators, history=history, engine=args.engine, model=model, temperature=args.temperature)
            history.append({"role": "assistant", "content": reply})
            print(f"rbot: {reply}")
    else:
        prompt = None
        if args.prompt:
            prompt = args.prompt
        elif args.prompt_file:
            with open(args.prompt_file, 'r') as f:
                prompt = f.read().strip()
        elif args.stdin:
            stdin = sys.stdin.readlines()
            if stdin:
                prompt = "".join(stdin).strip()

        history.append({"role": "user", "content": prompt})
        reply = chat(prompt=prompt, decorators=decorators, history=history, engine=args.engine, model=model, temperature=args.temperature)
        pattern = re.compile(r"OUTPUT ?= ?\"\"\"((\n|.)*?)\"\"\"", re.MULTILINE)
        is_structured = pattern.search(reply)
        if is_structured:
            reply = is_structured[1].strip()
        print(reply)

if __name__ == "__main__":
    main()
