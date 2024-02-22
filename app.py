from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask_session import Session
from reportlab.pdfgen import canvas
import os
import docx2txt
import fitz
from docx import Document
from transformers import pipeline
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.config['SECRET_KEY'] = '123'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

def is_authenticated():
    return 'authenticated' in session

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_authenticated():
        return redirect(url_for('index'))

    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        if username == 'Akshat@123' and password == 'Infinity':
            session['authenticated'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', form=form, error='Invalid username or password')

    return render_template('login.html', form=form, error=None)


@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('login'))

history = []
qa_pipeline = pipeline("question-answering", model="bert-large-uncased-whole-word-masking-finetuned-squad")

@app.route('/', methods=['GET', 'POST'])
def index():
    if not is_authenticated():
        return redirect(url_for('login'))
    return render_template('index.html', history=history)


@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file:
        filename = file.filename
        file_path = os.path.join('uploads', filename)
        file.save(file_path)
        history.append({'filename': file_path})
        return render_template('index.html', history=history, filename=filename)

@app.route('/ask', methods=['POST'])
def ask():
    question = request.form['question']
    answer = answer_question(question)

    # Get the last entry in history
    last_entry = history[-1] if history else {}

    # Add the new entry with the question, answer, and filename
    entry = {'question': question, 'answer': answer, 'filename': last_entry.get('filename', '')}
    history.append(entry)

    # Return JSON response with question and answer
    return jsonify(entry)

@app.route('/export_pdf')
def export_pdf():
    pdf_filename = 'qa_history.pdf'
    create_pdf(history, pdf_filename)
    return send_file(pdf_filename, as_attachment=True)

def answer_question(question):
    # Assuming you want to use the filename from the last entry in history
    last_entry = history[-1]
    filename = last_entry.get('filename', '')

    if filename.lower().endswith('.pdf'):
        return extract_answer_from_pdf(filename, question)
    elif filename.lower().endswith('.docx'):
        return extract_answer_from_docx(filename, question)
    elif filename.lower().endswith('.doc'):
        return extract_answer_from_doc(filename, question)
    else:
        return "Unsupported document format"

def extract_answer_from_pdf(filename, question):
    text = ""
    with fitz.open(filename) as pdf_document:
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            text += page.get_text()

    result = qa_pipeline(question=question, context=text)
    answer = result["answer"]

    if not answer:
        answer = "Could not find relevant information in the document."

    return answer

def extract_answer_from_docx(filename, question):
    text = docx2txt.process(filename)
    result = qa_pipeline(question=question, context=text)
    answer = result["answer"]

    if not answer:
        answer = "Could not find relevant information in the document."

    return answer

def extract_answer_from_doc(filename, question):
    doc = Document(filename)
    text = " ".join([paragraph.text for paragraph in doc.paragraphs])
    result = qa_pipeline(question=question, context=text)
    answer = result["answer"]

    if not answer:
        answer = "Could not find relevant information in the document."

    return answer

def create_pdf(history, pdf_filename):
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
    styles = getSampleStyleSheet()

    story = []

    for entry in history:
        question = entry.get('question', '')
        answer = entry.get('answer', '')

        if question and answer:  # Check if both question and answer are present
            entry_text = f"<font size=12><strong>Question:</strong> {question}<br/><strong>Answer:</strong> {answer}</font>"
            story.append(Paragraph(entry_text, styles['Normal']))
            story.append(Spacer(1, 12))

    doc.build(story)

if __name__ == '__main__':
    app.run(debug=True)
