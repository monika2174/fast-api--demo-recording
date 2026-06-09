from sqlalchemy import create_engine, text

def main():
    engine = create_engine('postgresql+psycopg2://postgres:1234567890@localhost:5432/new')
    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE cart DROP CONSTRAINT IF EXISTS cart_product_id_fkey'))
        conn.execute(text('ALTER TABLE cart ADD CONSTRAINT cart_product_id_fkey FOREIGN KEY (product_id) REFERENCES product(id)'))
        print('constraint updated')
        rows = conn.execute(text("SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'cart'::regclass"))
        for row in rows:
            print(row)

if __name__ == '__main__':
    main()
