PROTO_OUT=./

SRC = main.py logger.py

PYLINT_IGNORE=

protoc:
	python3 -m grpc_tools.protoc -I./protos --python_out=$(PROTO_OUT) --grpc_python_out=$(PROTO_OUT) \
		./protos/common_messages.proto ./protos/market_service.proto ./protos/client_service.proto

clean-protoc:
	rm -f $(PROTO_OUT)*_pb2.py $(PROTO_OUT)*_pb2_grpc.py

clean-logs:
	rm -rf logs_node_*

format:
	black $(SRC)
