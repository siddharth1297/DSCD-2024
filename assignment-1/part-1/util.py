"""
UTIL: Common and helper function
"""
import enum


class ItemCategory(enum.Enum):
    """Item Type"""

    ANY = "ANY"  # It is only for search
    ELECTRONICS = "ELECTRONICS"
    FASHION = "FASHION"
    OTHERS = "OTHERS"

    def __str__(self):
        return self.value


def item_category(request) -> ItemCategory:
    """
    From any pb msg, get item category
    """
    if request.HasField("electronics"):
        return ItemCategory.ELECTRONICS
    if request.HasField("fashion"):
        return ItemCategory.FASHION
    if request.HasField("others"):
        return ItemCategory.OTHERS
    return ItemCategory.ANY


def set_pb_msg_category(request, category: ItemCategory) -> None:
    """
    Sets category variable (oneof mode) for any pb message
    """
    if category == ItemCategory.ELECTRONICS:
        request.electronics = True
    elif category == ItemCategory.FASHION:
        request.fashion = True
    elif category == ItemCategory.OTHERS:
        request.other = True
    else:
        request.any = True
