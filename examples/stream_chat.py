"""Stream chat completions from a local LightLLM-Gateway server."""

import asyncio

import httpx


async def main() -> None:
    payload = {
        "model": "llama3.1",
        "messages": [{"role": "user", "content": "Write one short sentence about local LLMs."}],
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            "http://127.0.0.1:8000/v1/chat/completions",
            json=payload,
            headers={"Authorization": "Bearer sk-demo"},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    print(line, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
