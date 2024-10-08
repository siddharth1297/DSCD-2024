# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: reducer.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


import common_messages_pb2 as common__messages__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='reducer.proto',
  package='MapReduce',
  syntax='proto3',
  serialized_options=None,
  serialized_pb=_b('\n\rreducer.proto\x12\tMapReduce\x1a\x15\x63ommon_messages.proto\"=\n\x10\x44oReduceTaskArgs\x12\x11\n\treduce_id\x18\x01 \x01(\x05\x12\x16\n\x0emapper_address\x18\x02 \x03(\t\"=\n\x08\x43\x65ntroid\x12\r\n\x05index\x18\x01 \x01(\x05\x12\"\n\x08\x63\x65ntroid\x18\x02 \x01(\x0b\x32\x10.MapReduce.Point\"f\n\x11\x44oReduceTaskReply\x12!\n\x06status\x18\x01 \x01(\x0e\x32\x11.MapReduce.Status\x12.\n\x11updated_centroids\x18\x02 \x03(\x0b\x32\x13.MapReduce.Centroid2Y\n\x0eReducerService\x12G\n\x08\x44oReduce\x12\x1b.MapReduce.DoReduceTaskArgs\x1a\x1c.MapReduce.DoReduceTaskReply\"\x00\x62\x06proto3')
  ,
  dependencies=[common__messages__pb2.DESCRIPTOR,])




_DOREDUCETASKARGS = _descriptor.Descriptor(
  name='DoReduceTaskArgs',
  full_name='MapReduce.DoReduceTaskArgs',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='reduce_id', full_name='MapReduce.DoReduceTaskArgs.reduce_id', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='mapper_address', full_name='MapReduce.DoReduceTaskArgs.mapper_address', index=1,
      number=2, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=51,
  serialized_end=112,
)


_CENTROID = _descriptor.Descriptor(
  name='Centroid',
  full_name='MapReduce.Centroid',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='index', full_name='MapReduce.Centroid.index', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='centroid', full_name='MapReduce.Centroid.centroid', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=114,
  serialized_end=175,
)


_DOREDUCETASKREPLY = _descriptor.Descriptor(
  name='DoReduceTaskReply',
  full_name='MapReduce.DoReduceTaskReply',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='status', full_name='MapReduce.DoReduceTaskReply.status', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='updated_centroids', full_name='MapReduce.DoReduceTaskReply.updated_centroids', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=177,
  serialized_end=279,
)

_CENTROID.fields_by_name['centroid'].message_type = common__messages__pb2._POINT
_DOREDUCETASKREPLY.fields_by_name['status'].enum_type = common__messages__pb2._STATUS
_DOREDUCETASKREPLY.fields_by_name['updated_centroids'].message_type = _CENTROID
DESCRIPTOR.message_types_by_name['DoReduceTaskArgs'] = _DOREDUCETASKARGS
DESCRIPTOR.message_types_by_name['Centroid'] = _CENTROID
DESCRIPTOR.message_types_by_name['DoReduceTaskReply'] = _DOREDUCETASKREPLY
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

DoReduceTaskArgs = _reflection.GeneratedProtocolMessageType('DoReduceTaskArgs', (_message.Message,), dict(
  DESCRIPTOR = _DOREDUCETASKARGS,
  __module__ = 'reducer_pb2'
  # @@protoc_insertion_point(class_scope:MapReduce.DoReduceTaskArgs)
  ))
_sym_db.RegisterMessage(DoReduceTaskArgs)

Centroid = _reflection.GeneratedProtocolMessageType('Centroid', (_message.Message,), dict(
  DESCRIPTOR = _CENTROID,
  __module__ = 'reducer_pb2'
  # @@protoc_insertion_point(class_scope:MapReduce.Centroid)
  ))
_sym_db.RegisterMessage(Centroid)

DoReduceTaskReply = _reflection.GeneratedProtocolMessageType('DoReduceTaskReply', (_message.Message,), dict(
  DESCRIPTOR = _DOREDUCETASKREPLY,
  __module__ = 'reducer_pb2'
  # @@protoc_insertion_point(class_scope:MapReduce.DoReduceTaskReply)
  ))
_sym_db.RegisterMessage(DoReduceTaskReply)



_REDUCERSERVICE = _descriptor.ServiceDescriptor(
  name='ReducerService',
  full_name='MapReduce.ReducerService',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  serialized_start=281,
  serialized_end=370,
  methods=[
  _descriptor.MethodDescriptor(
    name='DoReduce',
    full_name='MapReduce.ReducerService.DoReduce',
    index=0,
    containing_service=None,
    input_type=_DOREDUCETASKARGS,
    output_type=_DOREDUCETASKREPLY,
    serialized_options=None,
  ),
])
_sym_db.RegisterServiceDescriptor(_REDUCERSERVICE)

DESCRIPTOR.services_by_name['ReducerService'] = _REDUCERSERVICE

# @@protoc_insertion_point(module_scope)
