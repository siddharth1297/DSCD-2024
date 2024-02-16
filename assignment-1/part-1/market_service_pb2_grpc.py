# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import common_messages_pb2 as common__messages__pb2
import market_service_pb2 as market__service__pb2


class MarketServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.registerSeller = channel.unary_unary(
                '/shopping_platform.MarketService/registerSeller',
                request_serializer=common__messages__pb2.ClientDetails.SerializeToString,
                response_deserializer=market__service__pb2.BooleanResponse.FromString,
                )
        self.sellItem = channel.unary_unary(
                '/shopping_platform.MarketService/sellItem',
                request_serializer=common__messages__pb2.ItemDetails.SerializeToString,
                response_deserializer=market__service__pb2.ItemOpResp.FromString,
                )
        self.updateItem = channel.unary_unary(
                '/shopping_platform.MarketService/updateItem',
                request_serializer=common__messages__pb2.ItemDetails.SerializeToString,
                response_deserializer=market__service__pb2.ItemOpResp.FromString,
                )
        self.deleteItem = channel.unary_unary(
                '/shopping_platform.MarketService/deleteItem',
                request_serializer=common__messages__pb2.ItemDetails.SerializeToString,
                response_deserializer=market__service__pb2.ItemOpResp.FromString,
                )
        self.displaySellerItems = channel.unary_unary(
                '/shopping_platform.MarketService/displaySellerItems',
                request_serializer=common__messages__pb2.ClientDetails.SerializeToString,
                response_deserializer=market__service__pb2.ItemsList.FromString,
                )
        self.searchItem = channel.unary_unary(
                '/shopping_platform.MarketService/searchItem',
                request_serializer=market__service__pb2.SearchItemReq.SerializeToString,
                response_deserializer=market__service__pb2.ItemsList.FromString,
                )
        self.buyItem = channel.unary_unary(
                '/shopping_platform.MarketService/buyItem',
                request_serializer=market__service__pb2.BuyerItemOpReq.SerializeToString,
                response_deserializer=market__service__pb2.ItemOpResp.FromString,
                )
        self.addToWishList = channel.unary_unary(
                '/shopping_platform.MarketService/addToWishList',
                request_serializer=market__service__pb2.BuyerItemOpReq.SerializeToString,
                response_deserializer=market__service__pb2.ItemOpResp.FromString,
                )
        self.rateItem = channel.unary_unary(
                '/shopping_platform.MarketService/rateItem',
                request_serializer=market__service__pb2.BuyerItemOpReq.SerializeToString,
                response_deserializer=market__service__pb2.ItemOpResp.FromString,
                )


class MarketServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def registerSeller(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def sellItem(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def updateItem(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def deleteItem(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def displaySellerItems(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def searchItem(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def buyItem(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def addToWishList(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def rateItem(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_MarketServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'registerSeller': grpc.unary_unary_rpc_method_handler(
                    servicer.registerSeller,
                    request_deserializer=common__messages__pb2.ClientDetails.FromString,
                    response_serializer=market__service__pb2.BooleanResponse.SerializeToString,
            ),
            'sellItem': grpc.unary_unary_rpc_method_handler(
                    servicer.sellItem,
                    request_deserializer=common__messages__pb2.ItemDetails.FromString,
                    response_serializer=market__service__pb2.ItemOpResp.SerializeToString,
            ),
            'updateItem': grpc.unary_unary_rpc_method_handler(
                    servicer.updateItem,
                    request_deserializer=common__messages__pb2.ItemDetails.FromString,
                    response_serializer=market__service__pb2.ItemOpResp.SerializeToString,
            ),
            'deleteItem': grpc.unary_unary_rpc_method_handler(
                    servicer.deleteItem,
                    request_deserializer=common__messages__pb2.ItemDetails.FromString,
                    response_serializer=market__service__pb2.ItemOpResp.SerializeToString,
            ),
            'displaySellerItems': grpc.unary_unary_rpc_method_handler(
                    servicer.displaySellerItems,
                    request_deserializer=common__messages__pb2.ClientDetails.FromString,
                    response_serializer=market__service__pb2.ItemsList.SerializeToString,
            ),
            'searchItem': grpc.unary_unary_rpc_method_handler(
                    servicer.searchItem,
                    request_deserializer=market__service__pb2.SearchItemReq.FromString,
                    response_serializer=market__service__pb2.ItemsList.SerializeToString,
            ),
            'buyItem': grpc.unary_unary_rpc_method_handler(
                    servicer.buyItem,
                    request_deserializer=market__service__pb2.BuyerItemOpReq.FromString,
                    response_serializer=market__service__pb2.ItemOpResp.SerializeToString,
            ),
            'addToWishList': grpc.unary_unary_rpc_method_handler(
                    servicer.addToWishList,
                    request_deserializer=market__service__pb2.BuyerItemOpReq.FromString,
                    response_serializer=market__service__pb2.ItemOpResp.SerializeToString,
            ),
            'rateItem': grpc.unary_unary_rpc_method_handler(
                    servicer.rateItem,
                    request_deserializer=market__service__pb2.BuyerItemOpReq.FromString,
                    response_serializer=market__service__pb2.ItemOpResp.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'shopping_platform.MarketService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class MarketService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def registerSeller(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/shopping_platform.MarketService/registerSeller',
            common__messages__pb2.ClientDetails.SerializeToString,
            market__service__pb2.BooleanResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def sellItem(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/shopping_platform.MarketService/sellItem',
            common__messages__pb2.ItemDetails.SerializeToString,
            market__service__pb2.ItemOpResp.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def updateItem(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/shopping_platform.MarketService/updateItem',
            common__messages__pb2.ItemDetails.SerializeToString,
            market__service__pb2.ItemOpResp.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def deleteItem(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/shopping_platform.MarketService/deleteItem',
            common__messages__pb2.ItemDetails.SerializeToString,
            market__service__pb2.ItemOpResp.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def displaySellerItems(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/shopping_platform.MarketService/displaySellerItems',
            common__messages__pb2.ClientDetails.SerializeToString,
            market__service__pb2.ItemsList.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def searchItem(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/shopping_platform.MarketService/searchItem',
            market__service__pb2.SearchItemReq.SerializeToString,
            market__service__pb2.ItemsList.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def buyItem(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/shopping_platform.MarketService/buyItem',
            market__service__pb2.BuyerItemOpReq.SerializeToString,
            market__service__pb2.ItemOpResp.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def addToWishList(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/shopping_platform.MarketService/addToWishList',
            market__service__pb2.BuyerItemOpReq.SerializeToString,
            market__service__pb2.ItemOpResp.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def rateItem(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/shopping_platform.MarketService/rateItem',
            market__service__pb2.BuyerItemOpReq.SerializeToString,
            market__service__pb2.ItemOpResp.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
