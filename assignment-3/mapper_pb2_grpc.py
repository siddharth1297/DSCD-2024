# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

import mapper_pb2 as mapper__pb2


class MapperServicesStub(object):
  # missing associated documentation comment in .proto file
  pass

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.DoMap = channel.unary_unary(
        '/MapReduce.MapperServices/DoMap',
        request_serializer=mapper__pb2.DoMapTaskArgs.SerializeToString,
        response_deserializer=mapper__pb2.DoMapTaskReply.FromString,
        )
    self.GetData = channel.unary_unary(
        '/MapReduce.MapperServices/GetData',
        request_serializer=mapper__pb2.GetDataArgs.SerializeToString,
        response_deserializer=mapper__pb2.GetDataReply.FromString,
        )


class MapperServicesServicer(object):
  # missing associated documentation comment in .proto file
  pass

  def DoMap(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def GetData(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_MapperServicesServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'DoMap': grpc.unary_unary_rpc_method_handler(
          servicer.DoMap,
          request_deserializer=mapper__pb2.DoMapTaskArgs.FromString,
          response_serializer=mapper__pb2.DoMapTaskReply.SerializeToString,
      ),
      'GetData': grpc.unary_unary_rpc_method_handler(
          servicer.GetData,
          request_deserializer=mapper__pb2.GetDataArgs.FromString,
          response_serializer=mapper__pb2.GetDataReply.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'MapReduce.MapperServices', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))