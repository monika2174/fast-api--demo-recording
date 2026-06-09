from sqlalchemy import create_engine, text

def main():
    engine = create_engine('postgresql+psycopg2://postgres:1234567890@localhost:5432/new')
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"))
        print([r[0] for r in rows])
        try:
            count = conn.execute(text('SELECT count(*) FROM cart')).scalar()
            print('cart count', count)
        except Exception as e:
            print('cart error', e)
        try:
            rows = conn.execute(text('SELECT id, name, price, quantity FROM product ORDER BY id'))
            print('product rows')
            for row in rows:
                print(row)
        except Exception as e:
            print('product error', e)

if __name__ == '__main__':
    main()
