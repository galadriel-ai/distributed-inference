"""
Script to compare the latency of different models inference providers
Usage:
```shell
PYTHONPATH=. python scripts/latency_competition.py
```
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import mean

from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI

env_path = Path("../.env")
load_dotenv(dotenv_path=env_path)


class Client:
    def __init__(self, name, client_object, model_name):
        self.name = name
        self.client_object = client_object
        self.model_name = model_name


clients = [
    Client(
        name="Galadriel",
        client_object=OpenAI(
            base_url="https://api.galadriel.com/v1",
            api_key=os.getenv("GALADRIEL_API_KEY"),
        ),
        model_name="llama3.1:70b",
    ),
    Client(
        name="Groq",
        client_object=Groq(api_key=os.getenv("GROQ_API_KEY")),
        model_name="llama-3.1-70b-versatile",
    ),
    Client(
        name="Together AI",
        client_object=OpenAI(
            base_url="https://api.together.xyz/v1",
            api_key=os.getenv("TOGETHER_API_KEY"),
        ),
        model_name="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    ),
    Client(
        name="Deep Infra",
        client_object=OpenAI(
            base_url="https://api.deepinfra.com/v1/openai/",
            api_key=os.getenv("DEEP_INFRA_API_KEY"),
        ),
        model_name="meta-llama/Meta-Llama-3-70B-Instruct",
    ),
]

input = [
    {
        "role": "system",
        "content": "You are an expert product manager at FAANG who will help me plan the core requirements for a new product. I just want you to provide me with detailed requirements (no fluff), needed to build an MVP of the product in under a week. The idea will be provided by the user. The output must be in markdown format and should be under 200 words",
    },
    {
        "role": "user",
        "content": "I want to build a new product that will allow me to track my sleep",
    },
]

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def worker(idx, model, messages, client, durations):
    start_time = time.time()
    client.chat.completions.create(
        model=model,
        messages=messages,
    )
    end_time = time.time()
    durations.append(end_time - start_time)


def main():
    threads = []
    for client in clients:
        durations = []

        logging.info(f"Testing client: {client.name}")

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = []
            for _ in range(10):  # Num of tasks per client
                futures.append(
                    executor.submit(
                        worker,
                        _,
                        client.model_name,
                        input,
                        client.client_object,
                        durations,
                    )
                )

            # Wait for all tasks to complete
            for future in futures:
                future.result()

        threads.append((None, durations, client))

    # Calculate and print the report for each client
    for _, durations, client in threads:
        min_duration = min(durations)
        max_duration = max(durations)
        avg_duration = mean(durations)

        logging.info(
            f"Client: {client.name}\n\t- Min Duration: {min_duration}s\n\t- Max Duration: {max_duration}s\n\t- Avg Duration: {avg_duration}s"
        )


def single_test(client):
    print(f"Test client: {client.name}")

    response = client.client_object.chat.completions.create(
        model=client.model_name,
        messages=input,
    )
    print(response)


if __name__ == "__main__":
    main()
