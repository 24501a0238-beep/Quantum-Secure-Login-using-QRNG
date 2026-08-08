from flask import Flask, render_template, request, session, redirect, url_for
from qiskit import QuantumCircuit, transpile
from qiskit_aer import Aer 
import base64
from io import BytesIO
import matplotlib.pyplot as plt
import random
import string
import time

app=Flask(__name__,template_folder='templates')
app.secret_key = 'quantum_secret_key_123'  # Change this in production

# In-memory storage for demo purposes (use a database in production)
otp_storage = {}
captcha_storage = {}

def generate_quantum_random_number(num_bits=8):
    """Generate a random number using quantum circuit"""
    # Create a quantum circuit with num_bits qubits
    qc = QuantumCircuit(num_bits, num_bits)
    
    # Apply Hadamard gate to each qubit to create superposition
    for qubit in range(num_bits):
        qc.h(qubit)
    
    # Measure all qubits
    qc.measure(range(num_bits), range(num_bits))

    backend = Aer.get_backend("aer_simulator")
    qc = transpile(qc, backend)
    job = backend.run(qc, shots=1, memory=True)
    result = job.result()
    bits = result.get_memory()[0] # Returns bitstring, e.g. '0110'
    return int(bits, 2)
    
    # Execute the circuit on a quantum simulator
    #simulator = Aer.get_backend('qasm_simulator')
    #result = execute(qc, simulator, shots=1).result()
    #counts = result.get_counts(qc)
    
    # Convert the binary result to an integer
    #random_binary = list(counts.keys())[0]
    #return int(random_binary, 2)

def generate_captcha():
    """Generate a CAPTCHA code using quantum random numbers"""
    # Generate 6 random characters
    captcha_text = ''
    for _ in range(6):
        # Get a quantum random number and map it to a character
        rand_num = generate_quantum_random_number(6)  # 6 bits = 0-63
        # Map to alphanumeric characters
        if rand_num < 10:
            captcha_text += str(rand_num)
        elif rand_num < 36:
            captcha_text += chr(ord('A') + rand_num - 10)
        else:
            captcha_text += chr(ord('a') + rand_num - 36)
    
    # Store CAPTCHA in session
    session['captcha'] = captcha_text
    return captcha_text

def generate_otp():
    """Generate a 6-digit OTP using quantum random numbers"""
    otp = ''
    for _ in range(6):
        # Get a quantum random number between 0-9
        rand_num = generate_quantum_random_number(4)  # 4 bits = 0-15
        # If number is >9, use modulo 10
        otp += str(rand_num % 10)
    
    # Store OTP with timestamp
    otp_storage[session['mobile']] = {
        'otp': otp,
        'timestamp': time.time()
    }
    return otp

def verify_otp(mobile, user_otp):
    """Verify if the OTP is correct and not expired"""
    if mobile not in otp_storage:
        return False
    
    otp_data = otp_storage[mobile]
    
    # Check if OTP is expired (5 minutes)
    if time.time() - otp_data['timestamp'] > 300:
        del otp_storage[mobile]
        return False
    
    # Check if OTP matches
    if otp_data['otp'] == user_otp:
        del otp_storage[mobile]
        return True
    
    return False

@app.route('/')
def login():
    # Generate a new CAPTCHA for each login attempt
    captcha_text = generate_captcha()
    return render_template('login.html', captcha=captcha_text)

@app.route('/login', methods=['POST'])
def login_post():
    mobile = request.form.get('mobile')
    captcha_input = request.form.get('captcha')
    
    # Validate mobile number (simple validation for demo)
    if not mobile or len(mobile) < 10:
        return render_template('login.html', 
                              error="Please enter a valid mobile number",
                              captcha=generate_captcha())
    
    # Validate CAPTCHA
    if 'captcha' not in session or captcha_input != session['captcha']:
        return render_template('login.html', 
                              error="Invalid CAPTCHA code",
                              captcha=generate_captcha())
    
    # Store mobile in session
    session['mobile'] = mobile
    
    # Generate and send OTP (in real app, send via SMS)
    otp = generate_otp()
    print(f"OTP for {mobile}: {otp}")  # For demo purposes
    
    return redirect(url_for('otp_verification'))

@app.route('/otp')
def otp_verification():
    if 'mobile' not in session:
        return redirect(url_for('login'))
    return render_template('otp.html')

@app.route('/verify-otp', methods=['POST'])
def verify_otp_post():
    if 'mobile' not in session:
        return redirect(url_for('login'))
    
    otp_input = request.form.get('otp')
    mobile = session['mobile']
    
    if verify_otp(mobile, otp_input):
        return redirect(url_for('welcome'))
    else:
        return render_template('otp.html', error="Invalid OTP")

@app.route('/welcome')
def welcome():
    if 'mobile' not in session:
        return redirect(url_for('login'))
    return render_template('welcome.html', mobile=session['mobile'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
