#
#   Hello World server in Python
#   Binds REP socket to tcp://*:5555
#   Expects b"Hello" from client, replies with b"World"
#

import asyncio

import zmq.asyncio


async def main():
    context = zmq.asyncio.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")

    while True:
        #  Wait for next request from client
        message = await socket.recv()
        print(f"Received request: {message}")

        #  Do some 'work'
        await asyncio.sleep(1)

        #  Send reply back to client
        await socket.send_string("World")


if __name__ == "__main__":
    asyncio.run(main())
