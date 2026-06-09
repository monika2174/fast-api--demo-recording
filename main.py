from fastapi import Depends, FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import Column, Integer, String, Float, ForeignKey, create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from pydantic import BaseModel
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os

app = FastAPI()

# Directory where images will be saved
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ------------------- DATABASE SETUP -------------------
DATABASE_URL = "postgresql+psycopg2://postgres:1234567890@localhost:5432/new"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ------------------- MODELS -------------------
class Product(Base):
    __tablename__ = "product"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    price = Column(Float)
    quantity = Column(Integer)
    image_path = Column(String, nullable=True)  # ✅ added image_path column

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    password = Column(String, nullable=False)
    role = Column(String, default="user")
    cart_items = relationship("Cart", back_populates="user")

class Cart(Base):
    __tablename__ = "cart"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("product.id"))
    quantity = Column(Integer, default=1)

    user = relationship("User", back_populates="cart_items")
    product = relationship("Product")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("product.id"))
    quantity = Column(Integer)
    created_at = Column(String, default=datetime.utcnow().isoformat())
    status = Column(String, default="pending")

    user = relationship("User")
    product = relationship("Product")

Base.metadata.create_all(bind=engine, checkfirst=True)

# ------------------- MIDDLEWARE -------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins = [
    "http://localhost:8080",
    "http://localhost:3000"
    ],

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------- PASSWORD UTILS -------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str):
    if len(password) > 72:
        raise HTTPException(status_code=400, detail="Password too long (max 72 characters)")
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

# ------------------- JWT UTILS -------------------
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

bearer_scheme = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        role = payload.get("role", "user")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or role != "user":
        raise HTTPException(status_code=403, detail="Not authorized as user")
    return user

def get_current_superadmin(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        role = payload.get("role")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    if role != "superadmin":
        raise HTTPException(status_code=403, detail="Not authorized as superadmin")

    user = db.query(User).filter(User.id == user_id, User.role == "superadmin").first()
    if not user:
        raise HTTPException(status_code=404, detail="Superadmin not found")
    return user

# ------------------- SCHEMAS -------------------
class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    image_path: Optional[str] = None

class UserRegister(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class CartAdd(BaseModel):
    product_id: int
    quantity: int = 1

class CartUpdate(BaseModel):
    quantity: int

class SuperAdminRegister(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    password: str

# ------------------- ROOT -------------------
@app.get("/")
def read_root():
    return {"message": "welcome to my vs code"}

# ------------------- AUTH ROUTES -------------------
@app.post("/register")
def register_user(user: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    new_user = User(name=user.name, email=user.email, phone=user.phone, password=hashed_password, role="user")
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully", "user": {"id": new_user.id, "email": new_user.email}}

@app.post("/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email, User.role == "user").first()
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token({"sub": str(db_user.id), "role": "user"})
    return {"access_token": access_token, "token_type": "bearer", "role": "user"}

@app.post("/superadmin/login")
def superadmin_login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email, User.role == "superadmin").first()
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid superadmin credentials")

    access_token = create_access_token({"sub": str(db_user.id), "role": "superadmin"})
    return {"access_token": access_token, "token_type": "bearer", "role": "superadmin"}

@app.post("/superadmin/register")
def register_superadmin(user: SuperAdminRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    new_superadmin = User(name=user.name, email=user.email, phone=user.phone, password=hashed_password, role="superadmin")
    db.add(new_superadmin)
    db.commit()
    db.refresh(new_superadmin)
    return {"message": "Superadmin registered successfully", "superadmin": {"id": new_superadmin.id, "email": new_superadmin.email, "role": new_superadmin.role}}

# ------------------- CART & ORDER ROUTES -------------------
@app.post("/cart/add")
def add_to_cart(cart_item: CartAdd, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == cart_item.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    cart_entry = Cart(user_id=current_user.id, product_id=product.id, quantity=cart_item.quantity)
    db.add(cart_entry)
    db.commit()
    db.refresh(cart_entry)

    # Auto-place order silently with status = pending
    order = Order(user_id=current_user.id, product_id=product.id, quantity=cart_item.quantity, status="pending")
    db.add(order)
    db.commit()
    db.refresh(order)

    return {
        "message": "Product added to cart",
        "cart_id": cart_entry.id,
        "user_id": current_user.id,
        "user_email": current_user.email,
        "product_id": product.id,
        "product_name": product.name,
        "product_image": product.image_path,
        "quantity": cart_entry.quantity,
        "order_status": order.status
    }


@app.post("/orders/place")
def place_order(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cart_items = db.query(Cart).filter(Cart.user_id == current_user.id).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    orders = []
    for item in cart_items:
        order = Order(user_id=current_user.id, product_id=item.product_id, quantity=item.quantity, status="pending")
        db.add(order)
        orders.append(order)
        db.delete(item)  # clear cart after placing order

    db.commit()

    return {
        "message": "Order placed successfully",
        "user_id": current_user.id,
        "user_email": current_user.email,
        "orders": [
            {
                "order_id": o.id,
                "product_id": o.product_id,
                "product_name": o.product.name,
                "product_image": o.product.image_path,   # ✅ include image
                "quantity": o.quantity,
                "created_at": o.created_at,
                "status": o.status
            }
            for o in orders
        ]
    }

@app.get("/orders/history")
def get_order_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.user_id == current_user.id).all()
    return {
        "user_id": current_user.id,
        "user_email": current_user.email,
        "total_orders": len(orders),
        "orders": [
            {
                "order_id": o.id,
                "product_id": o.product_id,
                "product_name": o.product.name,
                "product_image": o.product.image_path,   # ✅ include image
                "quantity": o.quantity,
                "created_at": o.created_at,
                "status": o.status
            }
            for o in orders
        ]
    }

# ------------------- SUPERADMIN ROUTES -------------------

@app.post("/superadmin/products")
async def add_product_admin(
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    quantity: int = Form(...),
    image: UploadFile = File(...),
    current_admin: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    # ensure forward slashes in path
    image_path = os.path.join(UPLOAD_DIR, image.filename).replace("\\", "/")
    with open(image_path, "wb") as buffer:
        buffer.write(await image.read())

    db_product = Product(
        name=name,
        description=description,
        price=price,
        quantity=quantity,
        image_path=image_path
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    return {
        "message": "Product added successfully by superadmin",
        "product": {
            "id": db_product.id,
            "name": db_product.name,
            "description": db_product.description,
            "price": db_product.price,
            "quantity": db_product.quantity,
            "image_path": db_product.image_path
        }
    }

@app.put("/superadmin/products/{id}")
def update_product_admin(id: int, product_update: ProductUpdate, current_admin: User = Depends(get_current_superadmin), db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    update_data = product_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
    db.commit()
    db.refresh(db_product)
    return {"message": "Product updated by superadmin", "product": {
        "id": db_product.id,
        "name": db_product.name,
        "description": db_product.description,
        "price": db_product.price,
        "quantity": db_product.quantity,
        "image_path": db_product.image_path
    }}

@app.delete("/superadmin/products/{id}")
def delete_product_admin(id: int, current_admin: User = Depends(get_current_superadmin), db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(db_product)
    db.commit()
    return {"message": "Product deleted by superadmin"}

@app.get("/superadmin/orders/status/{status}")
def get_orders_by_status(status: str, current_admin: User = Depends(get_current_superadmin), db: Session = Depends(get_db)):
    valid_statuses = ["pending", "shipped", "delivered", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")

    orders = db.query(Order).filter(Order.status == status).all()
    return {
        "status": status,
        "total_orders": len(orders),
        "orders": [
            {
                "order_id": o.id,
                "user_email": o.user.email,
                "product_name": o.product.name,
                "product_image": o.product.image_path,   # ✅ include image
                "quantity": o.quantity,
                "created_at": o.created_at,
                "status": o.status
            }
            for o in orders
        ]
    }

@app.put("/superadmin/orders/{order_id}/status")
def update_order_status(order_id: int, current_status: str, new_status: str, current_admin: User = Depends(get_current_superadmin), db: Session = Depends(get_db)):
    valid_statuses = ["pending", "shipped", "delivered", "cancelled"]
    if current_status not in valid_statuses or new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")

    order = db.query(Order).filter(Order.id == order_id, Order.status == current_status).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found with status '{current_status}'")

    order.status = new_status
    db.commit()
    db.refresh(order)

    return {
        "message": f"Order {order_id} updated from {current_status} to {new_status}",
        "order": {
            "order_id": order.id,
            "user_email": order.user.email,
            "product_name": order.product.name,
            "product_image": order.product.image_path,   # ✅ include image
            "quantity": order.quantity,
            "status": order.status
        }
    }

# ------------------- BOOTSTRAP -------------------
def init_superadmin():
    with engine.connect() as conn:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        if 'role' not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user'"))
            conn.commit()
        order_columns = [col['name'] for col in inspector.get_columns('orders')]
        if 'status' not in order_columns:
            conn.execute(text("ALTER TABLE orders ADD COLUMN status VARCHAR DEFAULT 'pending'"))
            conn.commit()
        product_columns = [col['name'] for col in inspector.get_columns('product')]
        if 'image_path' not in product_columns:
            conn.execute(text("ALTER TABLE product ADD COLUMN image_path VARCHAR"))
            conn.commit()
        result = conn.execute(text("SELECT COUNT(*) FROM users WHERE role='superadmin'"))
        count = result.scalar()
        if count == 0:
            hashed_password = get_password_hash("admin123")
            conn.execute(text(
                "INSERT INTO users (name, email, phone, password, role) VALUES (:name, :email, :phone, :password, :role)"
            ), {
                "name": "Super Admin",
                "email": "admin@example.com",
                "phone": "9999999999",
                "password": hashed_password,
                "role": "superadmin"
            })
            conn.commit()

init_superadmin()

      