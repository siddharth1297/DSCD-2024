"""
Central Platform
"""
import enum
from typing import List
import argparse
import logging
from concurrent import futures
from threading import Lock
from typing_extensions import Self
import grpc

import common_messages_pb2
import client_service_pb2_grpc
import market_service_pb2
import market_service_pb2_grpc

import util
from util import ItemCategory

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - [%(pathname)s:%(funcName)s:%(lineno)d] - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger()

MAX_WORKERS = 2

DEFAULT_ITEM_ID = 0


class ClientType(enum.Enum):
    """Client Type"""

    BUYER = "BUYER"
    SELLER = "SELLER"

    def __str__(self):
        return self.value


class Client:
    """Represents Buyers and Sellers"""

    def __init__(self, address: str, unique_id: str, client_type: ClientType):
        self.address = address
        self.unique_id = unique_id
        self.type = client_type

    def __str__(self):
        if self.unique_id == "":
            return self.address
        return self.address + ", uuid = " + self.unique_id

    def __hash__(self):
        return hash(self.address + self.unique_id)

    def __eq__(self, other):
        if other.unique_id == "" or self.unique_id == "":
            return self.address == other.address
        return self.address == other.address and self.unique_id == other.unique_id
        # return (
        #    self.type == other.type
        #    and self.address == other.address
        #    and self.unique_id == other.unique_id
        # )


class Item:
    """Product"""

    class Rating:
        """Rating of an item"""

        def __init__(self, **kwargs):
            self.rating = None
            self.raters = set()
            if "rating" in kwargs:
                self.rating = kwargs["rating"]

        def __str__(self):
            return "Unrated" if self.rating is None else str(self.rating) + " / 5"

        def add_rating(self, rating: int, rater: Client) -> (bool, str):
            """
            Adds a new rating
            """
            assert rater.type == ClientType.BUYER
            if not 1 <= rating <= 5:
                return (False, "Invalid Rate")
            if rater in self.raters:
                return (False, "Buyer already rated")
            if self.rating is None:
                self.rating = rating
            else:
                self.rating = round(
                    ((self.rating * len(self.raters)) + rating)
                    / (len(self.raters) + 1),
                    1,
                )
            self.raters.add(rater)
            return (True, "")

    def __init__(self, **kwargs):
        self.item_id = kwargs["item_id"]
        self.product_name = kwargs["product_name"]
        self.category = kwargs["category"]
        self.quantity = kwargs["quantity"]
        self.description = kwargs["description"]
        self.price_per_unit = kwargs["price_per_unit"]
        self.seller = kwargs["seller"]
        self.rating = kwargs["rating"] if "rating" in kwargs else self.Rating()
        self.wishlist = []

    def __str__(self) -> str:
        return (
            f"Item ID: {self.item_id}, Name: {self.product_name}, Price: ${self.price_per_unit}, "
            f"Category: {self.category}, Description: {self.description}., "
            f"Quantity Remaining: {self.quantity}, Seller: [{self.seller}], "
            f"Rating: {self.rating}"
        )

    def update(self, **kwargs) -> bool:
        """
        Updates item details
        """
        self.price_per_unit = kwargs["price_per_unit"]
        self.quantity = kwargs["quantity"]
        return True

    def add_to_wish_list(self, buyer: Client) -> (bool, str):
        """
        Adds to wishlist
        """
        if not buyer in self.wishlist:
            self.wishlist.append(buyer)
        return (True, "")

    def rate(self, rating: int, rater: Client) -> (bool, str):
        """
        Add rating
        """
        return self.rating.add_rating(rating, rater)

    @classmethod
    def item_to_item_details(cls, item) -> common_messages_pb2.ItemDetails:
        """
        Converts Item to ItemDetails(proto)
        """
        item_details = common_messages_pb2.ItemDetails(
            item_id=item.item_id,
            product_name=item.product_name,
            quantity=item.quantity,
            description=item.description,
            price_per_unit=item.price_per_unit,
            rating=item.rating.rating,
            seller_details=common_messages_pb2.ClientDetails(
                address=item.seller.address, unique_id=item.seller.unique_id
            ),
        )
        util.set_pb_msg_category(item_details, item.category)
        return item_details

    @classmethod
    def item_detils_to_item(cls, request: common_messages_pb2.ItemDetails) -> Self:
        """
        Converts ItemDetails(proto) to Item
        """
        return cls(
            item_id=request.item_id,
            product_name=request.product_name,
            category=util.item_category(request),
            quantity=request.quantity,
            description=request.description,
            price_per_unit=request.price_per_unit,
            seller=Client(
                request.seller_details.address,
                request.seller_details.unique_id,
                ClientType.SELLER,
            ),
            rating=cls.Rating(rating=request.rating),
        )


class MarketService(market_service_pb2_grpc.MarketServiceServicer):
    """Market Services for client"""

    def __init__(self, server_ip: str, server_port: str, market):
        self.server_ip = server_ip
        self.server_port = server_port
        self.market = market
        self.mutex = Lock()

    def serve(self):
        """
        Runs in separate thread and serve request
        """
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=MAX_WORKERS))
        market_service_pb2_grpc.add_MarketServiceServicer_to_server(self, server)
        server.add_insecure_port(self.server_ip + ":" + self.server_port)
        server.start()
        logger.info("Server started, listening on %s", self.server_port)
        server.wait_for_termination()

    def registerSeller(
        self, request: common_messages_pb2.ClientDetails, context
    ) -> market_service_pb2.BooleanResponse:
        """RPC RegisterClient"""
        client = Client(request.address, request.unique_id, ClientType.SELLER)
        with self.mutex:
            res = self.market.register_seller(client)
        return market_service_pb2.BooleanResponse(status=res)

    def sellItem(
        self, request: common_messages_pb2.ItemDetails, context
    ) -> market_service_pb2.ItemOpResp:
        """RPC SellItem"""
        with self.mutex:
            status, item_id = self.market.sell_item(
                product_name=request.product_name,
                category=util.item_category(request),
                quantity=request.quantity,
                description=request.description,
                price_per_unit=request.price_per_unit,
                seller=Client(
                    request.seller_details.address,
                    request.seller_details.unique_id,
                    ClientType.SELLER,
                ),
            )
        return (
            market_service_pb2.ItemOpResp(status=status, item_id=item_id)
            if status
            else market_service_pb2.ItemOpResp(status=status)
        )

    def updateItem(
        self, request: common_messages_pb2.ItemDetails, context
    ) -> market_service_pb2.ItemOpResp:
        """RPC UpdateItem"""
        with self.mutex:
            status = self.market.update_item(
                item_id=request.item_id,
                quantity=request.quantity,
                price_per_unit=request.price_per_unit,
                seller=Client(
                    request.seller_details.address,
                    request.seller_details.unique_id,
                    ClientType.SELLER,
                ),
            )
        return market_service_pb2.ItemOpResp(status=status)

    def deleteItem(
        self, request: common_messages_pb2.ItemDetails, context
    ) -> market_service_pb2.ItemOpResp:
        """RPC DeleteItem"""
        with self.mutex:
            status = self.market.delete_item(
                item_id=request.item_id,
                seller=Client(
                    request.seller_details.address,
                    request.seller_details.unique_id,
                    ClientType.SELLER,
                ),
            )
        return market_service_pb2.ItemOpResp(status=status)

    def displaySellerItems(
        self, request: common_messages_pb2.ClientDetails, context
    ) -> market_service_pb2.ItemsList:
        """RPC DisplaySellerItems"""
        with self.mutex:
            items = self.market.seller_items(
                seller=Client(
                    request.address,
                    request.unique_id,
                    ClientType.SELLER,
                ),
            )
        return market_service_pb2.ItemsList(
            items=list(map(Item.item_to_item_details, items))
        )

    def searchItem(
        self, request: market_service_pb2.SearchItemReq, context
    ) -> market_service_pb2.ItemsList:
        """RPC SearchItem"""
        with self.mutex:
            items = self.market.search_items(
                product_name=request.product_name, category=util.item_category(request)
            )
        return market_service_pb2.ItemsList(
            items=list(map(Item.item_to_item_details, items))
        )

    def buyItem(
        self, request: market_service_pb2.BuyerItemOpReq, context
    ) -> market_service_pb2.ItemOpResp:
        """RPC BuyItem"""
        with self.mutex:
            status = self.market.buy_item(
                item_id=request.item_id,
                quantity=request.quantity,
                buyer=Client(request.buyer_details.address, "", ClientType.BUYER),
            )
        return market_service_pb2.ItemOpResp(status=status)

    def addToWishList(
        self, request: market_service_pb2.BuyerItemOpReq, context
    ) -> market_service_pb2.ItemOpResp:
        """RPC AddToWishList"""
        with self.mutex:
            status = self.market.add_to_wish_list(
                item_id=request.item_id,
                buyer=Client(request.buyer_details.address, "", ClientType.BUYER),
            )
        return market_service_pb2.ItemOpResp(status=status)

    def rateItem(
        self, request: market_service_pb2.BuyerItemOpReq, context
    ) -> market_service_pb2.ItemOpResp:
        """RPC RateItem"""
        with self.mutex:
            status = self.market.rate_item(
                item_id=request.item_id,
                rating=request.rating,
                buyer=Client(request.buyer_details.address, "", ClientType.BUYER),
            )
        return market_service_pb2.ItemOpResp(status=status)


class Market:
    """Market(Cental Platform)"""

    def __init__(self, server_ip: str, server_port: int):
        self.servicer = MarketService(server_ip, str(server_port), self)
        self.sellers = []
        self.unique_item_id_cnt = 1
        self.items_dict = {}

    def serve(self) -> None:
        """Start services"""
        self.servicer.serve()

    def register_seller(self, seller: Client) -> bool:
        """Register client"""
        if seller in self.sellers:
            logger.error("Seller join request from %s. FAIL. already present", seller)
            return False
        logger.info("Seller join request from %s", seller)
        self.sellers.append(seller)
        return True

    def sell_item(self, **kwargs) -> (bool, int):
        """
        Adds item to the offered items list
        Returns status and unique item id.
        Returns (false, DEFAULT_ITEM_ID) if any item with similar name sold by the same seller
            exists, otherwise returns (true, the unique item id).
        """
        seller = kwargs["seller"]
        logger.debug("Sell Item request from %s", seller)
        if not self.__verify_credentials(seller):
            logger.error("Sell Item request from %s FAIL. Invalid credentials", seller)
            return (False, DEFAULT_ITEM_ID)

        present = False
        item_id = DEFAULT_ITEM_ID

        # Check validity
        if (
            kwargs["product_name"] == ""
            or kwargs["quantity"] < 0
            or kwargs["price_per_unit"] < 0
            or kwargs["category"] == ItemCategory.ANY
        ):
            logger.error(
                "Sell Item request from %s Invalid items details. name: %s, quantity: %s, price: %s, category: %s",
                seller,
                kwargs["product_name"],
                kwargs["quantity"],
                kwargs["price_per_unit"],
                kwargs["category"],
            )
            return (False, DEFAULT_ITEM_ID)

        # Check if an item with same name and sold by the same seller exists
        for key, val in self.items_dict.items():
            present = (
                val.product_name == kwargs["product_name"] and val.seller == seller
            )
            if present:
                item_id = key
                break
        if present:
            logger.error(
                "Sell Item request from %s Item already Present item_id: %s",
                seller,
                item_id,
            )
            return (False, DEFAULT_ITEM_ID)
        kwargs["item_id"] = item_id = self.__get_new_unique_item_id()
        self.items_dict[item_id] = item = Item(**kwargs)
        logger.info("Sell Item request from %s Item %s", seller, item)
        return (True, item_id)

    def update_item(self, **kwargs) -> bool:
        """
        Updates item
        Returns update status
        Returns false, if item id isn't present, seller missmatches, otherwise returns true.
        """
        seller = kwargs["seller"]
        item_id = kwargs["item_id"]
        if not self.__verify_credentials(seller):
            logger.error(
                "Update Item %s FAIL. Invalid credentials. seller: %s", item_id, seller
            )
            return False

        # Check item_id
        if item_id not in self.items_dict:
            logger.error("Update Item %s FAIL. Invalid item id", item_id)
            return False

        item = self.items_dict[item_id]
        if item.seller != seller:
            logger.error(
                "Update Item %s FAIL. Seller Mismatch. ActualSeller: %s, requestedSeller: %s",
                item_id,
                item.seller,
                seller,
            )
            return False

        if kwargs["price_per_unit"] < 0 or kwargs["quantity"] < 0:
            logger.error(
                "Update Item %s FAIL. Invalid input. price: %s, qty: %s requestedSeller: %s",
                item_id,
                item.seller,
                kwargs["price_per_unit"],
                kwargs["quantity"],
                seller,
            )
            return False
        # Update the item details
        status = item.update(**kwargs)
        if status:
            self.items_dict[item_id] = item
            logger.info(
                "Update Item %s request from %s Item:: %s", item_id, seller, item
            )
        else:
            logger.error("Update Item %s FAIL.", item_id)

        # Send Notification
        Market.__send_client_notification(
            Item.item_to_item_details(item), item.wishlist
        )
        return status

    def delete_item(self, **kwargs) -> bool:
        """
        Deletes item
        Returns delete status
        Returns false, if item id isn't present, seller missmatches, otherwise returns true.
        """
        seller = kwargs["seller"]
        item_id = kwargs["item_id"]
        if not self.__verify_credentials(seller):
            logger.error(
                "Delete Item %s FAIL. Invalid credentials. seller: %s", item_id, seller
            )
            return False

        # Check item_id
        if item_id not in self.items_dict:
            logger.error("Delete Item %s FAIL. Invalid item id", item_id)
            return False

        item = self.items_dict[item_id]
        if item.seller != seller:
            logger.error(
                "Delete Item %s FAIL. Seller Mismatch. ActualSeller: %s, requestedSeller: %s",
                item_id,
                item.seller,
                seller,
            )
            return False

        # Delete the item
        del self.items_dict[item_id]
        logger.info("Delete Item %s request from %s", item_id, seller)
        return True

    def seller_items(self, **kwargs) -> List[Item]:
        """
        Seller's item
        Returns seller's items list
        """
        seller = kwargs["seller"]
        if not self.__verify_credentials(seller):
            logger.error(
                "Display Items request from %s FAIL. Invalid credentials.", seller
            )
            return []

        # Collect the items
        logger.info("Display Items request from %s", seller)
        items = list(
            filter(lambda item: item.seller == seller, self.items_dict.values())
        )
        return items

    def search_items(self, **kwargs) -> List[Item]:
        """
        Seller's item
        Returns seller's items list
        """
        product_name = kwargs["product_name"]
        category = kwargs["category"]
        logger.info(
            "Search request for Item name: %s, Category: %s.", product_name, category
        )
        items = []

        # Collect the items
        if product_name == "":
            if category == ItemCategory.ANY:
                items = self.items_dict.values()
            else:
                items = list(
                    filter(
                        lambda item: item.category == category,
                        self.items_dict.values(),
                    )
                )
        else:
            if category == ItemCategory.ANY:
                items = list(
                    filter(
                        lambda item: item.product_name == product_name,
                        self.items_dict.values(),
                    )
                )
            else:
                items = list(
                    filter(
                        lambda item: item.product_name == product_name
                        and item.category == category,
                        self.items_dict.values(),
                    )
                )
        return items

    def buy_item(self, **kwargs) -> bool:
        """
        Buy item
        Returns update status
        Returns false, if item id isn't present, invlaid quantity, inadequate quantity, otherwise returns true.
        """
        item_id = kwargs["item_id"]
        # Check item_id
        if item_id not in self.items_dict:
            logger.error("Buy Item %s FAIL. Invalid item id", item_id)
            return False

        item = self.items_dict[item_id]

        if kwargs["quantity"] <= 0:
            logger.error(
                "Buy Item FAIL. Invalid Qty. item_id: %s, qty: %s, buyer: %s",
                item_id,
                kwargs["quantity"],
                kwargs["buyer"],
            )
            return False

        if item.quantity < kwargs["quantity"]:
            logger.error(
                "Buy Item FAIL. Inadequate Qty. item_id: %s, availableQty: %s, requestedQty: %s, buyer: %s",
                item_id,
                item.quantity,
                kwargs["quantity"],
                kwargs["buyer"],
            )
            return False

        item.quantity -= kwargs["quantity"]
        logger.info(
            "Buyer request %s of item %s, from %s",
            kwargs["quantity"],
            item_id,
            kwargs["buyer"],
        )
        # Send Notification
        Market.__send_client_notification(
            Item.item_to_item_details(item), [item.seller]
        )
        return True

    def add_to_wish_list(self, **kwargs) -> bool:
        """
        add item to wish list
        If already in wish list, then doesn't append
        Returns false, if item id isn't present, otherwise returns true.
        Returns update status, always True.
        """
        item_id = kwargs["item_id"]
        # Check item_id
        if item_id not in self.items_dict:
            logger.error("Wishlist %s FAIL. Invalid item id", item_id)
            return (False, "invalid item id")

        status, err = self.items_dict[item_id].add_to_wish_list(buyer=kwargs["buyer"])
        if status:
            logger.info("Wishlist request of item %s from %s", item_id, kwargs["buyer"])
        else:
            logger.error(
                "Wishlist request of item %s from %s FAIL. %s",
                item_id,
                kwargs["buyer"],
                err,
            )
        return status

    def rate_item(self, **kwargs) -> bool:
        """
        Rate item
        Returns false, if item id isn't present, or already rated by the buyer
        """
        item_id = kwargs["item_id"]
        logger.debug(
            "%s rated item %s with %s stars", kwargs["buyer"], item_id, kwargs["rating"]
        )
        # Check item_id
        if item_id not in self.items_dict:
            logger.error("Rate Item %s FAIL. Invalid item id", item_id)
            return False

        status, err = self.items_dict[item_id].rate(kwargs["rating"], kwargs["buyer"])
        if status:
            logger.info(
                "%s rated item %s with %s stars",
                kwargs["buyer"],
                item_id,
                kwargs["rating"],
            )
        else:
            logger.error(
                "%s rating item %s with %s stars: FAIL. %s",
                kwargs["buyer"],
                item_id,
                kwargs["rating"],
                err,
            )
        logger.debug("Item: %s", self.items_dict[item_id])
        return status

    def __verify_credentials(self, client: Client) -> bool:
        """Verify if the seller has registered"""
        return client in self.sellers

    def __get_new_unique_item_id(self) -> int:
        """Returns a new unique id for a new item"""
        u_id = self.unique_item_id_cnt
        self.unique_item_id_cnt += 1
        return u_id

    @staticmethod
    def __send_client_notification(
        item_details_pb2: common_messages_pb2.ItemDetails, clients: List[Client]
    ) -> None:
        """
        Sends notification to the list of clients
        """
        for client in clients:
            try:
                with grpc.insecure_channel(client.address) as channel:
                    stub = client_service_pb2_grpc.ClientServiceStub(channel)
                    stub.notifyClient(item_details_pb2)
            except grpc.RpcError:
                logger.error("Client %s not available.", client)


def main(server_ip: str, server_port: int) -> None:
    """main"""
    market = Market(server_ip, server_port)
    market.serve()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="central platform for Online Shopping Platform",
        epilog="$ python3 market.py --ip 0.0.0.0 --port 8085",
    )
    parser.add_argument("-i", "--ip", help="server ip", required=True)
    parser.add_argument("-p", "--port", help="server port", required=True, type=int)
    args = parser.parse_args()
    main(args.ip, args.port)
