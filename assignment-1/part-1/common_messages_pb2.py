# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: common_messages.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x15\x63ommon_messages.proto\x12\x11shopping_platform\"3\n\rClientDetails\x12\x0f\n\x07\x61\x64\x64ress\x18\x01 \x01(\t\x12\x11\n\tunique_id\x18\x02 \x01(\t\"\x85\x02\n\x0bItemDetails\x12\x0f\n\x07item_id\x18\x01 \x01(\x05\x12\x14\n\x0cproduct_name\x18\x02 \x01(\t\x12\x15\n\x0b\x65lectronics\x18\x03 \x01(\x08H\x00\x12\x11\n\x07\x66\x61shion\x18\x04 \x01(\x08H\x00\x12\x10\n\x06others\x18\x05 \x01(\x08H\x00\x12\x10\n\x08quantity\x18\x06 \x01(\x05\x12\x13\n\x0b\x64\x65scription\x18\x07 \x01(\t\x12\x16\n\x0eprice_per_unit\x18\x08 \x01(\x02\x12\x38\n\x0eseller_details\x18\t \x01(\x0b\x32 .shopping_platform.ClientDetails\x12\x0e\n\x06rating\x18\n \x01(\x02\x42\n\n\x08\x63\x61tegoryb\x06proto3')



_CLIENTDETAILS = DESCRIPTOR.message_types_by_name['ClientDetails']
_ITEMDETAILS = DESCRIPTOR.message_types_by_name['ItemDetails']
ClientDetails = _reflection.GeneratedProtocolMessageType('ClientDetails', (_message.Message,), {
  'DESCRIPTOR' : _CLIENTDETAILS,
  '__module__' : 'common_messages_pb2'
  # @@protoc_insertion_point(class_scope:shopping_platform.ClientDetails)
  })
_sym_db.RegisterMessage(ClientDetails)

ItemDetails = _reflection.GeneratedProtocolMessageType('ItemDetails', (_message.Message,), {
  'DESCRIPTOR' : _ITEMDETAILS,
  '__module__' : 'common_messages_pb2'
  # @@protoc_insertion_point(class_scope:shopping_platform.ItemDetails)
  })
_sym_db.RegisterMessage(ItemDetails)

if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _CLIENTDETAILS._serialized_start=44
  _CLIENTDETAILS._serialized_end=95
  _ITEMDETAILS._serialized_start=98
  _ITEMDETAILS._serialized_end=359
# @@protoc_insertion_point(module_scope)