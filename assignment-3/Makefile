PROTO_OUT=./

SRC = run_master.py master.py logger.py worker.py

PYLINT_IGNORE=too-many-instance-attributes


protoc:
	python3 -m grpc_tools.protoc -I./protos --python_out=$(PROTO_OUT) --grpc_python_out=$(PROTO_OUT) \
		./protos/master.proto ./protos/mapper.proto ./protos/reducer.proto ./protos/common_messages.proto

clean-protoc:
	rm -f $(PROTO_OUT)*_pb2.py $(PROTO_OUT)*_pb2_grpc.py

clean-logs:
	rm -rf logs

format:
	black $(SRC)
