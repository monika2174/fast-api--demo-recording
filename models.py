from pydantic import BaseModel



class Product(BaseModel):
    id: int
    name: str
    description: str
    price: float
    quantity: int
    email: str
    password: str
    add to cart: str
    update cart: str
    remove from cart: str
    
