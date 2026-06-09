from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float
Base = declarative_base()

class Product(Base):
   __tablename__ = "product"

   id = Column(Integer, primary_key=True, index=True)
   name = Column(String(100))
   description = Column(String(200))
   price = Column(Float)
   quantity = Column(Integer)
   email = Column(String(100))
   password = Column(String(100))
   add_to_cart = Column(String(100))
   update_cart = Column(String(100))
   remove_from_cart = Column(String(100))