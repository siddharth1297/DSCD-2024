# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: raft.proto
# Protobuf Python Version: 4.25.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\nraft.proto\x12\x04raft\"_\n\x0fRequestVoteArgs\x12\x0c\n\x04term\x18\x01 \x01(\x05\x12\x13\n\x0b\x63\x61ndidateId\x18\x02 \x01(\x05\x12\x14\n\x0clastLogIndex\x18\x03 \x01(\x05\x12\x13\n\x0blastLogTerm\x18\x04 \x01(\x05\"U\n\x10RequestVoteReply\x12\x0c\n\x04term\x18\x01 \x01(\x05\x12\x13\n\x0bvoteGranted\x18\x02 \x01(\x08\x12\x1e\n\x16leaseRemainingDuration\x18\x03 \x01(\x05\"\xa5\x01\n\x11\x41ppendEntriesArgs\x12\x0c\n\x04term\x18\x01 \x01(\x05\x12\x10\n\x08leaderId\x18\x02 \x01(\x05\x12\x14\n\x0cprevLogIndex\x18\x03 \x01(\x05\x12\x13\n\x0bprevLogTerm\x18\x04 \x01(\x05\x12\x0f\n\x07\x65ntries\x18\x05 \x03(\t\x12\x14\n\x0cleaderCommit\x18\x06 \x01(\x05\x12\x1e\n\x16leaseRemainingDuration\x18\x07 \x01(\x05\"`\n\x12\x41ppendEntriesReply\x12\x0c\n\x04term\x18\x01 \x01(\x05\x12\x0f\n\x07success\x18\x02 \x01(\x08\x12\x15\n\rconflictIndex\x18\x03 \x01(\x05\x12\x14\n\x0c\x63onflictTerm\x18\x04 \x01(\x05\x32\x8f\x01\n\x0bRaftService\x12\x42\n\rAppendEntries\x12\x17.raft.AppendEntriesArgs\x1a\x18.raft.AppendEntriesReply\x12<\n\x0bRequestVote\x12\x15.raft.RequestVoteArgs\x1a\x16.raft.RequestVoteReplyb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'raft_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _globals['_REQUESTVOTEARGS']._serialized_start=20
  _globals['_REQUESTVOTEARGS']._serialized_end=115
  _globals['_REQUESTVOTEREPLY']._serialized_start=117
  _globals['_REQUESTVOTEREPLY']._serialized_end=202
  _globals['_APPENDENTRIESARGS']._serialized_start=205
  _globals['_APPENDENTRIESARGS']._serialized_end=370
  _globals['_APPENDENTRIESREPLY']._serialized_start=372
  _globals['_APPENDENTRIESREPLY']._serialized_end=468
  _globals['_RAFTSERVICE']._serialized_start=471
  _globals['_RAFTSERVICE']._serialized_end=614
# @@protoc_insertion_point(module_scope)
