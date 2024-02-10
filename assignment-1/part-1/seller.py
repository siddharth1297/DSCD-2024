"""
Seller
"""
import logging
import uuid
import argparse
from typing import List
import grpc

import market_service_pb2
import market_service_pb2_grpc

import market

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - [%(pathname)s:%(funcName)s:%(lineno)d] - %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger()


class SellerService:
    """Seller Services"""

    def __init__(self, seller, server_ip: str, server_port: int):
        self.seller = seller
        self.server_ip = server_ip
        self.server_port = str(server_port)
        self.server_address = server_ip + ":" + str(server_port)


class Seller:
    """Seller client"""

    def __init__(
        self,
        seller_server_ip: str,
        seller_server_port: int,
        market_server_ip: str,
        market_server_port: int,
    ):
        self.unique_id = str(uuid.uuid1())
        self.market_address = market_server_ip + ":" + str(market_server_port)
        self.servicer = SellerService(self, seller_server_ip, seller_server_port)

    def start(self):
        """
        start seller service
        """
        # TODO: Init service
        if not self.__register():
            return False
        return True

    def sell_item(self, **kwargs) -> bool:
        """
        Calls market to sell the given item
        """
        request = None
        try:
            request = market_service_pb2.ItemDetails(
                product_name=kwargs["product_name"],
                quantity=kwargs["quantity"],
                description=kwargs["description"],
                price_per_unit=kwargs["price_per_unit"],
                seller_details=market_service_pb2.ClientDetails(
                    address=self.servicer.server_address, unique_id=self.unique_id
                ),
            )
            if kwargs["category"] == market.ItemCategory.ELECTRONICS:
                request.electronics = True
            elif kwargs["category"] == market.ItemCategory.FASHION:
                request.fashion = True
            else:
                request.other = True
        except KeyError as key_err:
            logger.error("Item details not provided. %s", key_err)
            return False

        assert request is not None

        with grpc.insecure_channel(self.market_address) as channel:
            stub = market_service_pb2_grpc.MarketServiceStub(channel)
            response = stub.sellItem(request)
            if response.status:
                logger.info(
                    "Seller sellItem SUCCESS, unique_item_id: %s", response.item_id
                )
            else:
                logger.info("Seller sellItem FAIL")
            return response.status
        return False

    def display_sellers_items(self) -> List[market.Item]:
        """
        Calls market to get all the items sold by this seller
        """
        request = market_service_pb2.ClientDetails(
            address=self.servicer.server_address, unique_id=self.unique_id
        )
        with grpc.insecure_channel(self.market_address) as channel:
            stub = market_service_pb2_grpc.MarketServiceStub(channel)
            response = stub.displaySellerItems(request)
            items = list(map(market.Item.item_detils_to_item, response.items))
            logger.info("Seller Items\n-\n{}".format("\n-\n".join(map(str, items))))
            return items
        return []

    def __register(self) -> bool:
        """
        Register at the market
        """
        with grpc.insecure_channel(self.market_address) as channel:
            request = market_service_pb2.ClientDetails(
                address=self.servicer.server_address, unique_id=self.unique_id
            )
            stub = market_service_pb2_grpc.MarketServiceStub(channel)
            response = stub.registerSeller(request)
            if response.status:
                logger.info("Seller Register SUCCESS")
            else:
                logger.info("Seller Register FAIL")
            return response.status
        return False


def main(
    seller_server_ip: str,
    seller_server_port: int,
    market_server_ip: str,
    market_server_port: int,
):
    """
    main
    """
    seller = Seller(
        seller_server_ip, seller_server_port, market_server_ip, market_server_port
    )
    assert seller.start()
    assert not seller.start()

    seller.display_sellers_items()
    assert seller.sell_item(
        product_name="iPhone",
        quantity=1,
        description="This is iPhone 15",
        price_per_unit=1500,
        category=market.ItemCategory.ELECTRONICS,
    )
    seller.display_sellers_items()
    assert not seller.sell_item(
        product_name="iPhone",
        quantity=1,
        description="This is iPhone 15",
        price_per_unit=1500,
        category=market.ItemCategory.ELECTRONICS,
    )
    assert seller.sell_item(
        product_name="iPhoneeee",
        quantity=1,
        description="This is iPhone 15",
        price_per_unit=1500,
        category=market.ItemCategory.ELECTRONICS,
    )
    seller.display_sellers_items()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="seller for Online Shopping Platform",
        epilog="$ python3 seller.py --ip 0.0.0.0 --port 8090 --sip 0.0.0.0 --sport 8085",
    )
    parser.add_argument("-i", "--ip", help="seller server ip", required=True)
    parser.add_argument(
        "-p", "--port", help="seller server port", required=True, type=int
    )
    parser.add_argument("-si", "--sip", help="market server ip", required=True)
    parser.add_argument(
        "-sp", "--sport", help="market server port", required=True, type=int
    )
    args = parser.parse_args()
    main(args.ip, args.port, args.sip, args.sport)
