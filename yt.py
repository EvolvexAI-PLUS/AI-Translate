import asyncio
from google import genai
import time

client = genai.Client(api_key='AIzaSyCpjoxh8iLYfkSTpEcqo5k2Uw-zgl5hXKg')
model = "gemini-live-2.5-flash-preview"
config = {"response_modalities": ["TEXT"]}

start_chat_time = time.time()
print("Started chat session at", start_chat_time)

async def main():
    async with client.aio.live.connect(model=model, config=config) as session:
        print("Session started")
        # Add logic for chat or other operations here
        await session.close()

if __name__ == "__main__":
    asyncio.run(main())