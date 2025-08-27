#
#   Hello World client in Python
#   Connects REQ socket to tcp://localhost:5555
#   Sends "Hello" to server, expects "World" back
#
import asyncio
from random import randint

import zmq.asyncio


async def main():
    context = zmq.asyncio.Context()
    id = f"client-{randint(0, 1000)}"
    #  Socket to talk to server
    print("Connecting to hello world server...")
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5555")

    #  Do 10 requests, waiting each time for a response
    for request in range(20):
        print(f"Sending request {request} ...")
        await socket.send_string(f"Hello from {id}")

        #  Get the reply.
        message = await socket.recv()
        print(f"Received reply {request} [ {message} ]")


if __name__ == "__main__":
    asyncio.run(main())
