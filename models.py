from pydantic import BaseModel

class Customer(BaseModel):
    id: int
    name: str
    email: str
    phone: str
