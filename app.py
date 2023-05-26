"""
This file contains the code for the Flask server that handles
the conversations with the NPCs.
"""
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from npc_langchain import NpcLangChain as NPC

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.secret_key = 'secret key'
# npc = NpcLangChain(player_name="Player")
# npcs = {}


class SessionManager:
    """ Manages user sessions.
    """
    def __init__(self):
        self.sessions = {}

    def get_session(self, user_id):
        """ Returns the session for the given user ID.
        """
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                'npcs': {
                    'Ted': NPC('Ted'),
                    'Barry': NPC('Barry'),
                    'Mike': NPC('Mike'),
                },
                'curr_npc': 'Ted',
            }
        return self.sessions[user_id]

    def reset(self, user_id):
        """ Resets the session for the given user ID.
        """
        self.sessions[user_id] = {}


session_manager = SessionManager()


@app.route('/userId', methods=['GET', 'OPTIONS'])
@cross_origin()
def handle_user_id():
    """ Handles the user ID.
    Returns:
        A JSON response containing the user ID.
    """
    if request.method == 'GET':
        return jsonify({'userId': str(uuid.uuid4())}), 200
    return jsonify({'error': 'invalid request method'}), 400


@app.route('/conversations/<user_id>', methods=['GET', 'POST', 'OPTIONS'])
@cross_origin()
def handle_npc_conversations(user_id):
    """ Handles the conversations with the specified NPC.
    Args:
        npc_name (str): The name of the NPC to handle the conversations with.
    Returns:
        A JSON response containing the conversations with the specified NPC.
    """
    sess = session_manager.get_session(user_id)
    npc_name = sess['curr_npc']
    npc = sess['npcs'].get(npc_name)
    if request.method == 'GET':
        # 获取和这个NPC的对话
        if npc:
            return jsonify(npc.conversation), 200
        return jsonify({'error': f'NPC {npc_name} not found'}), 404

    if request.method == 'POST':
        if request.json is None:
            return jsonify({'error': 'invalid JSON in request body'}), 400
        message = request.json.get('message')
        if message:
            # 将消息添加到这个NPC的对话中
            if npc:
                response = npc(message)
                print(response)
                return jsonify({'message': response}), 201
            return jsonify({'error': f'NPC {npc_name} not found'}), 404
        return jsonify({'error': 'Message is required'}), 400


@app.route('/changeNPC/<user_id>', methods=['POST', 'OPTIONS'])
@cross_origin()
def change_npc(user_id):
    """ Changes the NPC that the user is talking to.
    Returns:
        A JSON response indicating whether the NPC was successfully changed.
    """
    sess = session_manager.get_session(user_id)
    if request.method == 'POST':
        if request.json is None:
            return jsonify({'error': 'invalid JSON in request body'}), 400
        new_name = request.json.get('npc_name')
        print(new_name)
        if new_name:
            # 在这里添加你改变NPC的逻辑
            sess['curr_npc'] = new_name
            npc = sess['npcs'].get(new_name)
            return jsonify({
                'npc_name': npc.npc_name,
                'config_str': npc.config_str,
                'conversation': npc.conv_history,
            }), 200
        return jsonify({'error': 'NPC name is required'}), 400
    return jsonify({'ok': 'ok'}), 200


@app.route('/reset/<user_id>', methods=['POST', 'OPTIONS'])
@cross_origin()
def reset(user_id):
    """
    Resets the conversation with the specified NPC.
    Args:
        npc_name (str): The name of the NPC to reset the conversation with.

    Returns:
        A JSON response indicating whether the conversation was
            successfully reset.
    """
    sess = session_manager.get_session(user_id)
    npc_name = sess['curr_npc']
    npc = sess['npcs'].get(npc_name)
    if request.method == 'POST':
        # Reset the conversation with the specified NPC
        npc.reset(npc_name=npc_name)
        return jsonify({'message': 'Conversations reset'}), 200
    else:
        return jsonify({'ok': 'ok'}), 200


@app.route('/getConfigStr/<user_id>', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_config_str(user_id):
    """
    Gets the config_str of the specified NPC.
    Args:
        user_id (str): The name of the NPC to get the config_str of.

    Returns:
        A JSON response containing the config_str of the specified NPC.
    """
    sess = session_manager.get_session(user_id)
    npc_name = sess['curr_npc']
    npc = sess['npcs'].get(npc_name)
    if request.method == 'GET':
        # Get the config_str of the specified NPC
        return jsonify({'config_str': npc.config_str}), 200
    else:
        return jsonify({'ok': 'ok'}), 200


@app.route('/setConfigStr/<user_id>', methods=['POST', 'OPTIONS'])
@cross_origin()
def set_config_str(user_id):
    """
    Sets the config_str of the specified NPC.
    Args:
        user_id (str): The name of the NPC to set the config_str of.

    Returns:
        A JSON response indicating whether the config_str was successfully set.
    """
    sess = session_manager.get_session(user_id)
    npc_name = sess['curr_npc']
    npc = sess['npcs'].get(npc_name)
    if request.method == 'POST':
        # Set the config_str of the specified NPC
        if request.json is None:
            return jsonify({'error': 'invalid JSON in request body'}), 400
        config_str = request.json.get('config_str')
        if config_str:
            npc.reset(npc_name=npc_name, config_str=config_str)
            return jsonify({'message': 'config_str set'}), 200
        return jsonify({'error': 'config_str is required'}), 400
    else:
        return jsonify({'ok': 'ok'}), 200


@app.route('/getTaskStatus/<user_id>', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_task_status(user_id):
    """
    Gets the task_status of the specified NPC.
    Args:
        user_id (str): The name of the NPC to get the task_status of.

    Returns:
        A JSON response containing the task_status of the specified NPC.
    """
    sess = session_manager.get_session(user_id)
    npc_name = sess['curr_npc']
    npc = sess['npcs'].get(npc_name)
    if request.method == 'GET':
        # Get the task_status of the specified NPC
        return jsonify({'task_status': npc.task_status}), 200
    return jsonify({'ok': 'ok'}), 200


@app.route('/setTaskStatus/<user_id>', methods=['POST', 'OPTIONS'])
@cross_origin()
def set_task_status(user_id):
    """
    Sets the task_status of the specified NPC.
    Args:
        user_id (str): The name of the NPC to set the task_status of.

    Returns:
        A JSON response indicating whether the task_status
        was successfully set.
    """
    sess = session_manager.get_session(user_id)
    npc_name = sess['curr_npc']
    npc = sess['npcs'].get(npc_name)
    if request.method == 'POST':
        # Set the task_status of the specified NPC
        if request.json is None:
            return jsonify({'error': 'invalid JSON in request body'}), 400
        task_status = request.json.get('task_status')
        if task_status:
            npc.task_status = task_status
            print(npc_name, task_status)
            return jsonify({'message': 'task_status set'}), 200
        return jsonify({'error': 'task_status is required'}), 400
    return jsonify({'ok': 'ok'}), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8088)
