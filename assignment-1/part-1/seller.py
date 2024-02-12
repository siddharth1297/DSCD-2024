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
import util
from util import ItemCategory

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - [%(pathname)s:%(funcName)s:%(lineno)d] - %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger()

CMD_MODE = True


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
            util.set_pb_msg_category(request, kwargs["category"])
            # TODO: Add assert on category
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
            logger.info(
                "Seller Items %s", "\n-\n{}".format("\n-\n".join(map(str, items)))
            )
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


class Dialogue:
    """Dialogue"""

    def __init__(
        self,
        seller_server_ip: int,
        seller_server_port: int,
        market_server_ip: str,
        market_server_port: int,
    ):
        self.seller = Seller(
            seller_server_ip, seller_server_port, market_server_ip, market_server_port
        )

    @staticmethod
    def to_category(cat: int) -> ItemCategory:
        """
        Converts to category
        """
        if cat == 1:
            return ItemCategory.ELECTRONICS
        if cat == 2:
            return ItemCategory.FASHION
        return ItemCategory.OTHERS

    def start(self):
        """
        Start process
        """
        if not self.seller.start():
            return
        while True:
            cmd = input(
                "\nEnter 0-Exit 1-SellItem 2-UpdateItem 3-DeleteItem 4-DisplaySellerItem: "
            )
            if not cmd.isdigit():
                continue
            cmd = int(cmd)
            if cmd == 0:
                break

            if cmd == 1:
                product_name = input("product_name: ")
                ip_category = input(
                    "category (1-ELECTRONICS 2-FASHION 3-OTHERS): "
                )
                if not ip_category.isdigit():
                    continue
                category = Dialogue.to_category(int(ip_category))
                if category == ItemCategory.ANY:
                    continue
                qty = input("quantity: ")
                if not qty.isdigit():
                    continue
                qty = int(qty)
                if qty < 0:
                    continue
                desc = input("description: ")
                ppu = input("price_per_unit: ")
                
                if not ppu.isdigit():
                    continue
                ppu = float(ppu)
                if ppu < 0:
                    continue
                self.seller.sell_item(
                    product_name=product_name,
                    quantity=qty,
                    description=desc,
                    price_per_unit=ppu,
                    category=category,
                )
            if cmd == 4:
                self.seller.display_sellers_items()

def main(
    seller_server_ip: str,
    seller_server_port: int,
    market_server_ip: str,
    market_server_port: int,
):
    """
    main
    """
    if CMD_MODE:
        Dialogue(
            seller_server_ip, seller_server_port, market_server_ip, market_server_port
        ).start()
        return

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
