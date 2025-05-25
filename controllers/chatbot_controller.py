from odoo import http
from odoo.http import request
from flask import jsonify

class BeautyChatbotController(http.Controller):

    @http.route('/beauty_chatbot/message', type='json', auth="public", methods=['POST'])
    def chatbot_message(self, message):
        chatbot = request.env['beauty.chatbot'].sudo()
        response = chatbot.get_response(message)
        return jsonify({"response": response})
