from typing import List
from pydantic import BaseModel

class ShoppingCartItem(BaseModel):
    item_id: str
    quantity: int

class ShoppingCart(BaseModel):
    user_id: str
    items: List[ShoppingCartItem] = []

    def add_item(self, item_id: str, quantity: int) -> None:
        # Find the item in the cart
        for item in self.items:
            if item.item_id == item_id:
                # If item already in cart, increase the quantity
                item.quantity += quantity
                return
        # If item not in cart, add it
        self.items.append(ShoppingCartItem(item_id=item_id, quantity=quantity))
