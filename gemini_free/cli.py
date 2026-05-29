"""Simple CLI:  python -m gemini_free.cli "your prompt here" """

from __future__ import annotations

import asyncio
import sys

from .client import GeminiFree


async def _main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python -m gemini_free.cli "your prompt"')
        sys.exit(1)

    prompt = " ".join(sys.argv[1:])
    gemini = await GeminiFree.get()
    result = await gemini.ask(prompt)
    print(result["text"])


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
