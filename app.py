from flask import Flask, request, jsonify
import psycopg2
from con import set_connection
from loggerinstance import logger
import json

app = Flask(__name__)


def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except psycopg2.Error as e:
            conn = kwargs.get('conn')
            if conn:
                conn.rollback()
            logger.error(str(e))
            return jsonify({"error": "Database error"})
        except Exception as e:
            logger.error(str(e))
            return jsonify({"error": "Internal server error"})
        finally:
            conn = kwargs.get('conn')
            cur = kwargs.get('cur')

            if cur:
                cur.close()
            if conn:
                conn.close()

    return wrapper


# CREATE TABLE rooms (
#     id SERIAL PRIMARY KEY,
#     room_type TEXT NOT NULL,
#     is_available BOOLEAN NOT NULL,
#     CONSTRAINT unique_room_type UNIQUE (room_type)
# );
#
# CREATE TABLE bookings (
#     id SERIAL PRIMARY KEY,
#     room_type TEXT NOT NULL,
#     guest_name TEXT NOT NULL,
#     checkin_date DATE NOT NULL,
#     checkout_date DATE NOT NULL,
#     CONSTRAINT valid_booking_dates CHECK (checkin_date < checkout_date),
#     CONSTRAINT fk_rooms FOREIGN KEY (room_type) REFERENCES rooms(room_type) ON DELETE RESTRICT
# );


@app.route('/v1/room_availability', methods=['POST'])
@handle_exceptions
def get_room_availability():
    # {
    #     "room_type": "AC"
    # }
    data = request.get_json()
    room_type = data['room_type']
    cur, conn = set_connection()
    cur.execute("SELECT COUNT(*) FROM rooms WHERE room_type = %s AND is_available = true", (room_type,))
    count = cur.fetchone()[0]
    return jsonify({"room_type": room_type, "availability": count})


# {
#     "room_type": "AC",
#     "guest_name": "Akshith",
#     "checkin_date": "2023-04-01",
#     "checkout_date": "2023-04-03"
# }

@app.route('/v1/create_booking', methods=['POST'], endpoint='create_booking')
@handle_exceptions
def create_booking():
    data = request.get_json()
    room_type = data['room_type']
    guest_name = data['guest_name']
    checkin_date = data['checkin_date']
    checkout_date = data['checkout_date']
    cur, conn = set_connection()
    cur.execute("INSERT INTO bookings (room_type, guest_name, checkin_date, checkout_date) VALUES (%s, %s, %s, %s)",
                (room_type, guest_name, checkin_date, checkout_date))
    conn.commit()

    logger.info(f"Booking created: {data}")

    return jsonify({"message": "Booking created successfully"})


@app.route('/v1/cancel_booking/<int:booking_id>', methods=['DELETE'], endpoint='cancel_booking')
@handle_exceptions
def cancel_booking(booking_id):
    cur, conn = set_connection()
    cur.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
    booking = cur.fetchone()
    if booking:
        cur.execute("DELETE FROM bookings WHERE id = %s", (booking_id,))
        conn.commit()

        logger.info(f"Booking canceled: {booking}")

        return jsonify({"message": "Booking canceled successfully"})
    else:

        logger.warning(f"Booking not found: {booking_id}")

        return jsonify({"message": "Booking not found"})


@app.route('/v1/get_booking/guest/<string:guest_name>', methods=['GET'], endpoint='get_bookings_by_guest_name')
@handle_exceptions
def get_bookings_by_guest_name(guest_name):
    cur, conn = set_connection()
    cur.execute("SELECT * FROM bookings WHERE guest_name = %s", (guest_name,))
    bookings = cur.fetchall()
    logger.info(f"Booking data: {bookings}")
    return jsonify({"bookings": bookings})


@app.route('/v1/update_booking/<int:booking_id>', methods=['PUT'], endpoint='update_booking')
@handle_exceptions
def update_booking(booking_id):
    data = request.get_json()
    room_type = data['room_type']
    guest_name = data['guest_name']
    checkin_date = data['checkin_date']
    checkout_date = data['checkout_date']
    cur, conn = set_connection()
    cur.execute(
        "UPDATE bookings SET room_type = %s, guest_name = %s, checkin_date = %s, checkout_date = %s WHERE id = %s",
        (room_type, guest_name, checkin_date, checkout_date, booking_id))
    conn.commit()
    logger.info(f"Booking updated: {data}")
    return jsonify({"message": "Booking updated successfully"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
