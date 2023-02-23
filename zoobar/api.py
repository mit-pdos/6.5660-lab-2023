import rpclib

def call(method, **kwargs):
    with rpclib.RpcClientFifo('/run/fifo') as c:
        return c.call(method, **kwargs)
