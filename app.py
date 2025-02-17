from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import string

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

users = {}  # Stores user_id -> session ID
active_chats = {}  # Stores sender_id -> receiver_id mapping
chat_history = {}  # Stores chat messages

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('register')
def handle_register(data):
    user_id = data.get('user_id')
    if user_id and user_id not in users:
        users[user_id] = request.sid
        emit('registration_success', {'user_id': user_id}, room=request.sid)

@socketio.on('send_request')
def handle_send_request(data):
    sender_id = data.get('sender_id')
    receiver_id = data.get('receiver_id')

    if receiver_id in users:
        emit('receive_request', {'sender_id': sender_id}, room=users[receiver_id])
        emit('request_sent', {'success': True}, room=request.sid)
    else:
        emit('request_sent', {'success': False}, room=request.sid)

@socketio.on('accept_request')
def handle_accept_request(data):
    sender_id = data.get('sender_id')
    receiver_id = data.get('receiver_id')

    if sender_id in users and receiver_id in users:
        active_chats[sender_id] = receiver_id
        active_chats[receiver_id] = sender_id
        join_room(sender_id)
        join_room(receiver_id)

        chat_history[sender_id] = []
        chat_history[receiver_id] = []

        emit('request_accepted', {}, room=users[sender_id])
        emit('request_accepted', {}, room=users[receiver_id])

@socketio.on('send_message')
def handle_send_message(data):
    sender_id = data.get('sender_id')
    receiver_id = data.get('receiver_id')
    message = data.get('message')

    if sender_id in active_chats and active_chats[sender_id] == receiver_id:
        chat_history[sender_id].append({'sender': sender_id, 'message': message})
        chat_history[receiver_id].append({'sender': sender_id, 'message': message})

        emit('receive_message', {'sender_id': sender_id, 'message': message}, room=users[receiver_id])

@socketio.on('close_chat')
def handle_close_chat(data):
    user1 = data.get('user1')
    user2 = data.get('user2')

    if user1 in active_chats and active_chats[user1] == user2:
        encrypted_chat = encrypt_chat(chat_history[user1])

        emit('chat_closed', {'encrypted_chat': encrypted_chat}, room=users[user1])
        emit('chat_closed', {'encrypted_chat': encrypted_chat}, room=users[user2])

        leave_room(user1)
        leave_room(user2)

        del active_chats[user1]
        del active_chats[user2]
        del chat_history[user1]
        del chat_history[user2]

def encrypt_chat(messages):
    encrypted_data = []
    chars = string.ascii_letters + string.digits + "!@#$%^&*()"
    for msg in messages:
        encrypted_message = ''.join(random.choices(chars, k=12))  # 12-character random string
        encrypted_data.append({'sender': msg['sender'], 'message': encrypted_message})
    return encrypted_data

if __name__ == '__main__':
    socketio.run(app, debug=True)
