"""
Buyer
"""
import os
import threading
import time
import logging
from concurrent import futures
import uuid
import argparse
from typing import List
import grpc

import google.protobuf
import common_messages_pb2
import market_service_pb2
import market_service_pb2_grpc
import client_service_pb2_grpc

import market
import util
from util import ItemCategory

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - [%(pathname)s:%(funcName)s:%(lineno)d] - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger()


MAX_WORKERS = 2

CMD_MODE = True


class BuyerService(client_service_pb2_grpc.ClientServiceServicer):
    """Buyer Services"""

    def __init__(self, buyer, server_ip: str, server_port: int):
        self.buyer = buyer
        self.server_ip = server_ip
        self.server_port = str(server_port)
        self.server_address = server_ip + ":" + str(server_port)

    def serve(self) -> None:
        """start services"""
        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=MAX_WORKERS),
            options=(("grpc.so_reuseport", 0),),
        )
        client_service_pb2_grpc.add_ClientServiceServicer_to_server(self, server)
        server.add_insecure_port(self.server_ip + ":" + self.server_port)
        server.start()
        logger.info("Server started, listening on %s", self.server_port)
        server.wait_for_termination()

    def notifyClient(
        self, request: common_messages_pb2.ItemDetails, context
    ) -> google.protobuf.empty_pb2.Empty:
        """
        RPC notifyClient
        """
        logger.info(
            "\nThe Following Item has been updated:\n%s",
            market.Item.item_detils_to_item(request),
        )
        return google.protobuf.empty_pb2.Empty()


class Buyer:
    """Buyer client"""

    def __init__(
        self,
        buyer_server_ip: str,
        buyer_server_port: int,
        market_server_ip: str,
        market_server_port: int,
    ):
        self.unique_id = str(uuid.uuid1())
        self.market_address = market_server_ip + ":" + str(market_server_port)
        self.servicer = BuyerService(self, buyer_server_ip, buyer_server_port)
        self.service_thread = threading.Thread(target=self.servicer.serve)

    def start_service(self):
        """
        start buyer service
        """
        self.service_thread.start()
        time.sleep(2)
        return True

    def search_item(self, **kwargs) -> List[market.Item]:
        """
        Calls market to search item
        """
        request = None
        try:
            request = market_service_pb2.SearchItemReq(
                product_name=kwargs["product_name"],
            )
            util.set_pb_msg_category(request, kwargs["category"])
        except KeyError as key_err:
            logger.error("Details not provided. %s", key_err)
            return []

        assert request is not None

        with grpc.insecure_channel(self.market_address) as channel:
            stub = market_service_pb2_grpc.MarketServiceStub(channel)
            response = stub.searchItem(request)
            items = list(map(market.Item.item_detils_to_item, response.items))
            logger.info("Items %s", "\n-\n{}".format("\n-\n".join(map(str, items))))
            return items
        return []

    def buy_item(self, **kwargs) -> bool:
        """
        Calls market to buy item
        """
        request = None
        try:
            request = market_service_pb2.BuyerItemOpReq(
                item_id=kwargs["item_id"],
                buyer_details=common_messages_pb2.ClientDetails(
                    address=self.servicer.server_address
                ),
                quantity=kwargs["quantity"],
            )
        except KeyError as key_err:
            logger.error("Details not provided. %s", key_err)
            return False

        assert request is not None

        with grpc.insecure_channel(self.market_address) as channel:
            stub = market_service_pb2_grpc.MarketServiceStub(channel)
            response = stub.buyItem(request)
            if response.status:
                logger.info("SUCCESS")
            else:
                logger.error("FAIL")
            return response.status
        return False

    def add_to_wish_list(self, **kwargs) -> bool:
        """
        Calls market to add item to wiah list
        """
        request = None
        try:
            request = market_service_pb2.BuyerItemOpReq(
                item_id=kwargs["item_id"],
                buyer_details=common_messages_pb2.ClientDetails(
                    address=self.servicer.server_address
                ),
            )
        except KeyError as key_err:
            logger.error("Details not provided. %s", key_err)
            return False

        assert request is not None

        with grpc.insecure_channel(self.market_address) as channel:
            stub = market_service_pb2_grpc.MarketServiceStub(channel)
            response = stub.addToWishList(request)
            if response.status:
                logger.info("SUCCESS")
            else:
                logger.error("FAIL")
            return response.status
        return False

    def rate_item(self, **kwargs) -> bool:
        """
        Calls market to add item to wish list
        """
        request = None
        try:
            request = market_service_pb2.BuyerItemOpReq(
                item_id=kwargs["item_id"],
                buyer_details=common_messages_pb2.ClientDetails(
                    address=self.servicer.server_address
                ),
                rating=kwargs["rating"],
            )
        except KeyError as key_err:
            logger.error("Details not provided. %s", key_err)
            return []

        assert request is not None

        with grpc.insecure_channel(self.market_address) as channel:
            stub = market_service_pb2_grpc.MarketServiceStub(channel)
            response = stub.rateItem(request)
            if response.status:
                logger.info("SUCCESS")
            else:
                logger.error("FAIL")
            return response.status
        return False


class Dialogue:
    """Dialogue"""

    def __init__(
        self,
        buyer_server_ip: str,
        buyer_server_port: int,
        market_server_ip: str,
        market_server_port: int,
    ):
        self.buyer = Buyer(
            buyer_server_ip, buyer_server_port, market_server_ip, market_server_port
        )
        self.buyer.start_service()

    @staticmethod
    def to_category(cat: int) -> ItemCategory:
        """
        Converts to category
        """
        if cat == 1:
            return ItemCategory.ELECTRONICS
        if cat == 2:
            return ItemCategory.FASHION
        if cat == 3:
            return ItemCategory.OTHERS
        return ItemCategory.ANY

    def start(self):
        """
        Start process
        """
        while True:
            cmd = input(
                "\nEnter cls-Clear 0-Exit 1-SearchItem 2-BuyItem 3-AddToWishList 4-RateItem: "
            )
            if cmd == "cls":
                os.system("clear")
            if not cmd.isdigit():
                continue
            cmd = int(cmd)
            if cmd == 0:
                break

            if cmd == 1:
                product_name = input("product_name: ")
                ip_category = input(
                    "category (0-ANY 1-ELECTRONICS 2-FASHION 3-OTHERS): "
                )
                if not ip_category.isdigit():
                    continue
                category = Dialogue.to_category(int(ip_category))
                self.buyer.search_item(product_name=product_name, category=category)
            if cmd == 2:
                item_id = input("item_id: ")
                if not item_id.isdigit():
                    continue
                item_id = int(item_id)
                qty = input("quantity: ")
                if not qty.isdigit():
                    continue
                qty = int(qty)
                self.buyer.buy_item(item_id=item_id, quantity=qty)
            if cmd == 3:
                item_id = input("item_id: ")
                if not item_id.isdigit():
                    continue
                item_id = int(item_id)
                self.buyer.add_to_wish_list(item_id=item_id)
            if cmd == 4:
                item_id = input("item_id: ")
                if not item_id.isdigit():
                    continue
                item_id = int(item_id)
                rating = input("rating(1 <= rating <= 5): ")
                if not rating.isdigit():
                    continue
                rating = int(rating)
                self.buyer.rate_item(item_id=item_id, rating=rating)


def main(
    buyer_server_ip: str,
    buyer_server_port: int,
    market_server_ip: str,
    market_server_port: int,
):
    """
    main
    """
    if CMD_MODE:
        Dialogue(
            buyer_server_ip, buyer_server_port, market_server_ip, market_server_port
        ).start()
        return

    buyer = Buyer(
        buyer_server_ip, buyer_server_port, market_server_ip, market_server_port
    )
    # assert buyer.start()
    # assert not buyer.start()

    assert len(buyer.search_item(product_name="", category=ItemCategory.ANY)) == 0

    # start Client
    time.sleep(10)
    assert len(buyer.search_item(product_name="", category=ItemCategory.ANY)) == 2
    assert (
        len(buyer.search_item(product_name="", category=ItemCategory.ELECTRONICS)) == 2
    )
    assert len(buyer.search_item(product_name="", category=ItemCategory.FASHION)) == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="buyer for Online Shopping Platform",
        epilog="$ python3 buyer.py --ip 0.0.0.0 --port 8070 --mip 0.0.0.0 --mport 8085",
    )
    parser.add_argument("-i", "--ip", help="buyer server ip", required=True)
    parser.add_argument(
        "-p", "--port", help="buyer server port", required=True, type=int
    )
    parser.add_argument("-si", "--mip", help="market server ip", required=True)
    parser.add_argument(
        "-sp", "--mport", help="market server port", required=True, type=int
    )
    args = parser.parse_args()
    main(args.ip, args.port, args.mip, args.mport)
