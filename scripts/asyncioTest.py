import asyncio
import time


class UpperClass:
    def __init__(self):
        self.lower_instance = LowerClass(self.callback)

    async def callback(self):
        print("Upper method called")
        time.sleep(3)
        print("Upper method done")

class LowerClass:
    def __init__(self, callback):
        self.callback = callback

    async def lower_method(self):
        print("Lower method called")
        await self.callback()
        print("Lower method done")

async def main():
    upper = UpperClass()
    await upper.lower_instance.lower_method()
    time.sleep(3)

asyncio.run(main())
