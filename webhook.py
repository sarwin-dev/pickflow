from flask import Flask, request, abort
import hmac
import hashlib
import subprocess
import os

app = Flask(__name__)
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', '')

@app.route('/webhook', methods=['POST'])
def webhook():
    sig = request.headers.get('X-Hub-Signature-256', '')
    body = request.get_data()
    expected = 'sha256=' + hmac.new(
        WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        abort(403)
    subprocess.Popen([
        'bash', '-c',
        'cd /opt/pickflow && timeout 120 git pull && sudo systemctl restart pickflow'
    ])
    return 'OK', 200

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001)
