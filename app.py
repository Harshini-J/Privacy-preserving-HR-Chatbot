from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import LabelEncoder
from tensorflow.keras.preprocessing.sequence import pad_sequences
import lime
from lime.lime_text import LimeTextExplainer
from load_models_exp import tokenizer, final_model, label_encoder, explainer, responses, predict_probabilities
from datetime import date, timedelta, datetime
import re

app = Flask(__name__)

# Load employee data
def load_employee_data(file_path='employee_data.csv'):
    return pd.read_csv(file_path)

# Load FAQ data
def load_faq(file_path):
    return pd.read_excel(file_path, engine='openpyxl')
context_labels = ["holiday", "payslip"]
employee_data = load_employee_data()
hr_faq = load_faq('hr_faq_ex_1.xlsx')
leave_faq = load_faq('leave_faq_ex_1.xlsx')
context = ""
strikes = 0
hr_q, hr_a = list(hr_faq['question']), list(hr_faq['answer'])
leave_q, leave_a = list(leave_faq['question']), list(leave_faq['answer'])

# Helper function for similarity comparison
def cosine_similarity_sentences(sent1, sent2):
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([sent1, sent2])
    return cosine_similarity(vectors)[0, 1]

def lcs(str1, str2):
    m, n = len(str1), len(str2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # Fill the DP table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if str1[i - 1] == str2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # Backtrack to get the LCS string
    lcs_str = []
    i, j = m, n
    while i > 0 and j > 0:
        if str1[i - 1] == str2[j - 1]:
            lcs_str.append(str1[i - 1])
            i -= 1
            j -= 1
        elif dp[i - 1][j] > dp[i][j - 1]:
            i -= 1
        else:
            j -= 1

    lcs_string = "".join(reversed(lcs_str))
    return len(lcs_string) / max(len(str1), len(str2))

names = []
emp_ids = []
@app.route('/')
def home():
    global context
    if context != "banned":
        context = ""
        return render_template('index.html')
    else:
        return render_template('banned.html')

@app.route('/chat', methods=['POST'])
def chat():
    global strikes
    global context
    sf = 0
    user_input = request.json.get("message", "")
    employee_id = int(request.json.get("employee_id", ""))
    global names
    global emp_ids
    if names == []:
        employee_info = employee_data[employee_data['employee_id'] == employee_id]
        emp_name = employee_info.iloc[0]['name'].lower()
        for _ in employee_data['name']:
            names += _.lower().split(" ")
        names = set(names)
        for _ in emp_name.split(" "):
            if _ in names:
                names.remove(_)
    if emp_ids == []:
        for _ in employee_data['employee_id']:
            emp_ids.append(_)
        emp_ids = set(emp_ids)
        if employee_id in emp_ids:
            emp_ids.remove(employee_id)
    words = re.findall(r'\b\w+\b', user_input.lower())
    ids = re.findall(r'\b\d+\b', user_input.lower())
    for i in names:
        for j in words:
            if lcs(i, j) > 0.6:
                sf = 1
    for i in ids:
        if employee_id != int(i):
            sf = 1
    if sf == 1:
        strikes += 1
    if strikes >= 5 or context == "banned":
        context = "banned"
        return jsonify({"response": "Malicious activity has been detected. You have been banned from using the chatbot. Contact HR.", "context": "banned"})
    cont, response, imp_words = chatbot_response(employee_id, user_input.lower())
    return jsonify({"response": response, "context": cont, "imp_words": imp_words})

@app.route('/leave', methods=['POST'])
def leave():
    global context
    context = ""
    leave_type = request.json.get("type", "")
    leave_date = request.json.get("date", "")
    leave_days = int(request.json.get("days", ""))
    employee_id = int(request.json.get("employee_id", ""))
    employee_info = employee_data[employee_data['employee_id'] == employee_id]
    response = ""
    if not employee_info.empty:
        vacation_leave = int(employee_info.iloc[0]['vacation_leave'])
        sick_leave = int(employee_info.iloc[0]['sick_leave'])
        if leave_type == "Vacation":
            if leave_days <= vacation_leave:
                response = f"Request for vacation leave for {leave_days} day(s) from {leave_date} has been sent for approval."
            else:
                response = "You do not have enough leave balance."
        elif leave_type == "Sick":
            if leave_days <= sick_leave:
                response = f"Request for sick leave for {leave_days} day(s) from {leave_date} has been sent for approval."
            else:
                response = "You do not have enough leave balance."
        elif leave_type == "Casual":
            response = f"Request for casual leave for {leave_days} day(s) from {leave_date} has been sent for approval."
    else:
        response = "Employee details not found."
    return jsonify({"response": response})

@app.route('/payslip', methods=['POST'])
def payslip():
    global context
    context = ""
    month = request.json.get("month", "")
    employee_id = int(request.json.get("employee_id", ""))
    employee_info = employee_data[employee_data['employee_id'] == employee_id]
    response = ""
    if not employee_info.empty:
        response = f"Payslip info for {month} has been sent to your email"
    else:
        response = "Employee details not found."
    return jsonify({"response": response})

@app.route('/cancel', methods=['POST'])
def cancel():
    global context
    prev_context = context
    context = ""
    return jsonify({"response": "Action has been cancelled", "context": prev_context})

@app.route('/unload', methods=['POST'])
def unload():
    global context
    if context != "banned":
        context = ""
    return jsonify({})

# Function to fetch policy details
def get_policy_details(user_input):
    responses = []
    for i in range(len(hr_q)):
        if cosine_similarity_sentences(user_input, hr_q[i]) > 0.33:
            responses.append(hr_a[i])
    for i in range(len(leave_q)):
        if cosine_similarity_sentences(user_input, leave_q[i]) > 0.33:
            responses.append(leave_a[i])
    resp = "<br>".join(responses)
    if resp != "":
        resp += "<br>"
    return resp

# Function to fetch leave balance
def get_leave_details(employee_id):
    employee_info = employee_data[employee_data['employee_id'] == employee_id]
    if not employee_info.empty:
        vacation_leave = int(employee_info.iloc[0]['vacation_leave'])
        sick_leave = int(employee_info.iloc[0]['sick_leave'])
        return f"Your leave balance:<br>Vacation Leave: {vacation_leave}<br>Sick Leave: {sick_leave}<br>Do you want to apply for leave? (Y/N)<br>"
    return "Employee details not found."

def get_payslip_details(employee_id):
    employee_info = employee_data[employee_data['employee_id'] == employee_id]
    if not employee_info.empty:
        return "Do you want me to send your payslip to your email? (Y/N)"
    return "Employee details not found."

# Function to fetch manager details
def get_manager_details(employee_id):
    employee_info = employee_data[employee_data['employee_id'] == employee_id]
    if not employee_info.empty:
        manager_name = employee_info.iloc[0]['supervisor']
        manager_info = employee_data[employee_data['name'].str.lower() == manager_name.lower()]
        if not manager_info.empty:
            presence = ""
            if (manager_info.iloc[0]['presence'].lower() == "present") and (employee_info.iloc[0]['presence'].lower() == "present"):
                presence = f"You can meet {manager_info.iloc[0]['name']} at the office.<br>"
            return f"Manager: {manager_info.iloc[0]['name']}<br>Phone: {manager_info.iloc[0]['phone_number']}<br>Email: {manager_info.iloc[0]['email']}<br>{presence}"
    return "Manager details not found."

# Function to predict intent and provide response
def chatbot_response(employee_id, user_input=""):
    global context
    employee_info = employee_data[employee_data['employee_id'] == employee_id]
    if not employee_info.empty:
        if context == "":
            input_sequence = tokenizer.texts_to_sequences([user_input.lower()])
            padded_input = pad_sequences(input_sequence, maxlen=30, padding='post')
            prediction = final_model.predict(padded_input, verbose=0)
            predicted_label = label_encoder.inverse_transform([np.argmax(prediction)])[0]
            if predicted_label in context_labels:
                context = predicted_label
            if user_input != "":
                exp = explainer.explain_instance(user_input, predict_probabilities, num_features=6, top_labels=1)
                pred_label = exp.available_labels()[0]
                word_list = exp.as_list(label=pred_label)
                imp_words = []
                for i in word_list:
                    if round(i[1], 2) >= 0.02:
                        imp_words.append(i[0])
            else:
                imp_words = []
            base_response = responses.get(predicted_label, "I'm sorry, I don't understand your request.")
            return context, enhance_response(predicted_label, base_response, user_input, employee_id), imp_words
        elif user_input.lower() == "y":
            if context == "holiday":
                context = "leave-form"
                form = f"""<form id='leave-form' onsubmit='submitLeave(); return false;'>
                    <h3>Leave Request Form</h3>
                    <label for='leave-type'>Leave Type:</label>
                    <select id='leave-type' required>
                        <option value='Vacation'>Vacation</option>
                        <option value='Sick'>Sick</option>
                        <option value='Casual'>Casual</option>
                    </select><br><br>
                    <label for='leave-days'>Number of Days:</label>
                    <input type='number' value='1' min='1' max='50' id='leave-days' required"><br><br>
                    <label for='start-date'>Start Date:</label>
                    <input type='date' id='start-date' value={str(date.today() + timedelta(days = 1))} min={str(date.today() + timedelta(days = 1))} required><br><br>
                    <button class='cancel' type='button' onclick='cancel()'>Cancel</button>
                    <button id='submit' type='submit'>Submit</button>
                </form>"""
                return context, form, []
            if context == "payslip":
                context = "payslip-form"
                start_date = employee_info.iloc[0]['hire_date']
                form = f"""<form id='payslip-form' onsubmit='submitPayslip(); return false;'>
                    <h3>Payslip Request Form</h3>
                    <label for='month'>Month:</label>
                    <input type='month' id='month' min='{datetime.strptime(start_date, '%d-%m-%Y').date().strftime("%Y-%m")}' max='{(date(date.today().year, date.today().month, 1) - timedelta(days = 1)).strftime("%Y-%m")}' value='{(date(date.today().year, date.today().month, 1) - timedelta(days = 1)).strftime("%Y-%m")}' required><br><br>
                    <button class='cancel' type='button' onclick='cancel()'>Cancel</button>
                    <button id='submit' type='submit'>Submit</button>
                </form>"""
                return context, form, []
        else:
            context = ""
            return context, "Okay!", []
    else:
        return context, "You are not permitted to use this chatbot.", []

# Function to enhance response
def enhance_response(intent, base_response, user_input, employee_id=0):
    if intent == "leave_policy":
        return get_policy_details(user_input) + base_response
    if intent == "policy":
        return get_policy_details(user_input) + base_response
    elif intent == "manager_enquiry":
        return get_manager_details(employee_id) + base_response
    elif intent == "holiday":
        return get_leave_details(employee_id)
    elif intent == "payslip":
        return get_payslip_details(employee_id)
    return base_response

if __name__ == '__main__':
    app.run(debug=True)
