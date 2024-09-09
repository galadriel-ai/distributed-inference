import asyncio

import openai


async def main():
    is_stream = True
    client = openai.AsyncOpenAI(
        base_url="http://localhost:5000/v1", api_key="asdasd-asd123"
    )
    completion = await client.chat.completions.create(
        model="llama3",
        temperature=0,
        messages=[
            {"content": "You are a helpful assistant.", "role": "system"},
            {"content": "Hello!", "role": "user"},
        ],
        stream=is_stream,
    )
    if is_stream:
        async for chunk in completion:
            print(chunk, flush=True)
    else:
        print(completion)


if __name__ == "__main__":
    asyncio.run(main())
