from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/emotion', methods=['POST'])
def receive_emotion():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400
        
    status = data.get('status')
    score = data.get('score')
    
    print(f"Received from Jetson - Status: {status}, Score: {score}%")
    
    return jsonify({"status": "success", "message": "Data received"}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)