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

    def lower_method(self):
        print("Lower method called")
        asyncio.run(self.callback())
        print("Lower method done")

def main():
    upper = UpperClass()
    upper.lower_instance.lower_method()
    time.sleep(3)

main()
