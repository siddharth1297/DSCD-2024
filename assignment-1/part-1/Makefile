PROTO_OUT=./

SRC = market.py seller.py buyer.py util.py

PYLINT_IGNORE=too-many-instance-attributes,too-many-function-args,logging-too-many-args,too-many-branches

protoc:
	python3 -m grpc_tools.protoc -I./protos --python_out=$(PROTO_OUT) --grpc_python_out=$(PROTO_OUT) \
		./protos/common_messages.proto ./protos/market_service.proto ./protos/client_service.proto

clean-protoc:
	rm -f $(PROTO_OUT)*_pb2.py $(PROTO_OUT)*_pb2_grpc.py

format:
	black $(SRC)
lint:
	pylint market.py --disable=$(PYLINT_IGNORE)
	pylint seller.py --disable=$(PYLINT_IGNORE)
	pylint buyer.py  --disable=$(PYLINT_IGNORE)
	pylint util.py  --disable=$(PYLINT_IGNORE)
