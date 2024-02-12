"""
Buyer
"""
import time
import logging
import uuid
import argparse
from typing import List
import grpc

import market_service_pb2
import market_service_pb2_grpc

import market
import util
from util import ItemCategory

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - [%(pathname)s:%(funcName)s:%(lineno)d] - %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger()

CMD_MODE = True


class BuyerService:
    """Buyer Services"""

    def __init__(self, buyer, server_ip: str, server_port: int):
        self.buyer = buyer
        self.server_ip = server_ip
        self.server_port = str(server_port)
        self.server_address = server_ip + ":" + str(server_port)


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

    @staticmethod
    def start(self):
        """
        start buyer service
        """
        # TODO: Init service
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
            logger.error("SearchItem details not provided. %s", key_err)
            return []

        assert request is not None

        with grpc.insecure_channel(self.market_address) as channel:
            stub = market_service_pb2_grpc.MarketServiceStub(channel)
            response = stub.searchItem(request)
            items = list(map(market.Item.item_detils_to_item, response.items))
            logger.info(
                "Retrieved Items %s", "\n-\n{}".format("\n-\n".join(map(str, items)))
            )
            return items
        return []


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
        # assert buyer.start()

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
                "Enter 0-Exit 1-SearchItem 2-BuyItem 3-AddToWishList 4-RateItem: "
            )
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
