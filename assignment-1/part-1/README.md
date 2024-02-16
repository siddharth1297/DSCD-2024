# Part 1: Using gRPC to implement an Online Shopping Platform

## Author: Siddharth Nayak

## Install Dependencies
```
$ python3 -m pip install -r ../requirements.txt
```

## Run
```
$ python3 market.py -h
$ python3 buyer.py -h
$ python3 seller.py -h
```

## Design
#### market
Market class is the main class that implements the functionality according to the document.
MarketService class is responsible for handling the RPCs and convert parameters to the local format.
Push based notification.

### Client
Similarly, the class Buyer/Seller implements the functionality according to the document.
BuyerService/SellerService is responsible for handling the notifications
