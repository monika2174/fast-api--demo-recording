from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models import Product
import database_models
from database import session, engine
from sqlalchemy.orm import Session

app = FastAPI()
database_models.Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost:3001"],
)

@app.get("/")
def read_root():
    return {"message": "welcome to my vs code"}

products = [
    Product(id=1,name="phone", description="budget phone", price=99, quantity=10),
    Product(id=2,name="laptop", description="gaming laptop", price=999, quantity=5),
    Product(id=5,name="tablet", description="android tablet", price=199, quantity=15),
    Product(id=6,name="Pen", description="A blue ink pen", price=1.99, quantity=100),
]

def get_db():
    db = session()
    try:
        yield db
    finally:
            db.close()

def init_db():
    db = session()

    count = db.query(database_models.Product).count
    # Check if products table already has data
    existing_count = db.query(database_models.Product).count()
    if existing_count == 0:
        for product in products:
            db.add(database_models.Product(**product.model_dump()))
        db.commit()
    db.close()

init_db()
@app.get("/products")
def get_all_products(db: Session = Depends(get_db)):
    return db.query(database_models.Product).all()
    

@app.get("/products/{id}")
def get_product_by_id(id: int, db: Session = Depends(get_db)):
    db_product = db.query(database_models.Product).filter(database_models.Product.id == id).first()
    if db_product:
        return db_product
    return "product not found"
@app.post("/products")
def add_product(product: Product, db: Session = Depends(get_db)):
    db.add(database_models.Product(**product.model_dump()))
    db.commit()
    return product
@app.put("/products")
def update_product(id: int, product: Product, db: Session = Depends(get_db)):
    db_product = db.query(database_models.Product).filter(database_models.Product.id == id).first()
    if db_product:
        db_product.name = product.name
        db_product.description = product.description
        db_product.price = product.price
        db_product.quantity = product.quantity
        db.commit()
        return "Product updated successfully"
    return "product not found"
@app.delete("/products")
def delete_product(id: int, db: Session = Depends(get_db)):
    db_product = db.query(database_models.Product).filter(database_models.Product.id == id).first()
    if db_product:
        db.delete(db_product)
        db.commit()
    else:
        return "Product not found"
   