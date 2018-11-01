"""
    Author: dy1zan
    An asynchronous server implemented in Python
    which handles a variety of JSON requests.
"""

import asyncio
import json
import logging
from datetime import datetime

from . jrequest import request_type
from . import settings

"""
    GLOBAL CONSTANTS
"""
# The timeout interval for processing a request
REQUEST_TIMEOUT = 5 # in seconds
# Log format
LOG_FORMAT = "%(asctime)s %(levelname)s [%(module)s:%(lineno)d] %(message)s"


# Setup logging
logging.basicConfig(format=LOG_FORMAT, datefmt='[%H:%M:%S]')
log = logging.getLogger()
log.setLevel(logging.DEBUG)

class AServer(object):
    """
        Initalizes a new asynchronous server object.
        This server invokes methods with request_type decorators,
        when data is read. See requests.py
    """

    def __init__(self, port):

        log.debug(
            "The following request callbacks have been initialized, ",
            *request_type.get_types().keys()
        )

        self.port = port

        # constants
        self.BUFFER_SIZE = 2048

        # privates
        self.__writer = None
        self.__alive = False
        self.__loop = None

    def start(self):
        """
            Starts the asynchronous server on the given port.
        """

        self.__loop = asyncio.get_event_loop()
        self.__alive = True
        coro = asyncio.start_server(self.handle_connection, '127.0.0.1', self.port)
        asyncio.ensure_future(coro)
        log.info("Server has been started on 127.0.0.1:%d" % self.port)


    def stop(self):
        """
            Stops the asynchronous server.
        """
        self.__loop.stop()
        self.__alive = False
        log.info("Server has been stopped by request.")
        exit()


    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
            Handles a new client connection using NIO.
            When reading, it invokes the suitable request callback depending
            on the JSON request.

            :param: reader, the stream reader to read data from (in bytes)
            :param: writer, the stream writer to write data to (in bytes)
        """
        log.info("Incoming client connection from {}".format(writer.get_extra_info('peername')))

        try:
            self.__writer = writer

            while self.__alive:

                data = await reader.readuntil(b"\r\n")
                try:
                    data = data.decode('ascii')
                except UnicodeDecodeError:
                    continue
                
                log.debug("Received data from {}:{}".format(writer.get_extra_info('peername'), data))

                try:
                    # try parse the JSON, then get the type of request
                    data = json.loads(data)

                    # if it's a /terminate/ type, terminate the server
                    if(data['type'] == 'terminate'):
                        self.stop()

                    # invoke a callback belonging to a requset type if it is available
                    funcs = request_type.get_types()
                    if(funcs.get(data['type'])):
                        log.info("Invoking request callback, %s, with default timeout=%d." % (data['type'], REQUEST_TIMEOUT))
                        await asyncio.wait_for(funcs[data['type']](self, data), timeout=REQUEST_TIMEOUT)    

                except:
                    pass

        except (ConnectionError, asyncio.streams.IncompleteReadError):
            self.__writer = None
            log.info("There was a connection error. The client has timed out.")



    async def write(self, message: str):
        """
            Writes data to the stream writer
        """
        if self.__writer == None:
            return False

        # escape %
        message = message.replace("%", "%%")
        log.info("Writing to client: %s" % message)
        self.__writer.write(message.encode())
        
        try: await self.__writer.drain()
        except: return False
        return True


