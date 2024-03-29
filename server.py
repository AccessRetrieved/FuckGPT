from flask import Flask, render_template, request, url_for, redirect, send_file, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import pathlib
import requests
import webbrowser
import os
import json
from time import sleep
import sys
from random import randint
from colorama import init
from termcolor import cprint
from pyfiglet import figlet_format
from PyPDF2 import PdfReader, PdfFileReader
import textwrap
from fpdf import FPDF
from datetime import date, datetime
import socket
import docx
import sqlite3
import uuid
import re
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from python_http_client.exceptions import HTTPError
from nltk.corpus import stopwords
from nltk.cluster.util import cosine_distance
from nltk.tokenize import sent_tokenize
import numpy as np
import networkx as nx
import nltk

# TODO
# :Add account info page
# :Add paraphraser that's not detectable by this program on a separate page
# :UPDATE [paraphraser that's not detectable by this program on a separate page] Paraphraser works... not detectable by this program or others?

# init
app = Flask(__name__)
app.config.from_pyfile(os.path.join(os.getcwd(), 'config.py'))
allowedExtensions = {'txt', 'pdf', 'docx'}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
orig_stdout = None
req = [nltk.download(i) for i in ['punkt', 'stopwords']] # install nltk packages
table_connection = '''
CREATE TABLE IF NOT EXISTS "users" (
    id text PRIMARY KEY,
    username text,
    passwordHashed text,
    email text,
    emailVerified int,
    date text
);
'''

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# functions
def read_article(file_name):
    with open(file_name, 'r') as f:
        filedata = f.read()
    if not filedata:
        return []
    article = filedata.split(". ")
    sentences = []

    for sentence in article:
        sentences.append(sentence.replace("[^a-zA-Z]", " ").split(" "))
    sentences.pop() 
    
    return sentences


def sentence_similarity(sent1, sent2, stopwords=None):
    if stopwords is None:
        stopwords = []

    sent1 = [w.lower() for w in sent1]
    sent2 = [w.lower() for w in sent2]

    all_words = list(set(sent1 + sent2))

    vector1 = [0] * len(all_words)
    vector2 = [0] * len(all_words)

    for w in sent1:
        if w in stopwords:
            continue
        vector1[all_words.index(w)] += 1

    for w in sent2:
        if w in stopwords:
            continue
        vector2[all_words.index(w)] += 1

    return 1 - cosine_distance(vector1, vector2)


def build_similarity_matrix(sentences, stop_words):
    similarity_matrix = np.zeros((len(sentences), len(sentences)))

    for idx1 in range(len(sentences)):
        for idx2 in range(len(sentences)):
            if idx1 == idx2:
                continue
            similarity_matrix[idx1][idx2] = sentence_similarity(
                sentences[idx1], sentences[idx2], stop_words)

    return similarity_matrix

def generate_summary(file_name, top_n=5):
    stop_words = stopwords.words('english')
    summarize_text = []
    sentences = read_article(file_name)
    sentence_similarity_martix = build_similarity_matrix(sentences, stop_words)
    sentence_similarity_graph = nx.from_numpy_array(sentence_similarity_martix)
    scores = nx.pagerank(sentence_similarity_graph)

    ranked_sentence = sorted(((scores[i], s) for i, s in enumerate(sentences)), reverse=True)

    for i in range(top_n):
        summarize_text.append(" ".join(ranked_sentence[i][1]))

    return '. '.join(summarize_text)

def sendEmail(to, subject, htmlBody):
    message = Mail(from_email='fukgpt@gmail.com', to_emails=to,
                   subject=subject, html_content=htmlBody)

    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)

        return [response.status_code, response.body, response.headers]
    except Exception as e:
        sendgrid_client = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        try:
            response = sendgrid_client.send(message)
        except HTTPError as e:
            print(e.to_dict)

        print(json.dumps(message.get(), sort_keys=True, indent=4))


def getText(filename):
    doc = docx.Document(filename)
    fullText = []
    for para in doc.paragraphs:
        fullText.append(para.text)
    return '\n'.join(fullText)


def allowed_file(fileExt):
    return '.' in fileExt and fileExt.rsplit('.', 1)[1].lower() in allowedExtensions


def establishSqliteConnection(dbFile):
    conn = None
    try:
        conn = sqlite3.connect(dbFile)
        return conn
    except Exception as e:
        pass

    return conn


def pretty_print_POST(req):
    """
    At this point it is completely built and ready
    to be fired; it is "prepared".

    However pay attention at the formatting used in 
    this function because it is programmed to be pretty 
    printed and may differ from the actual request.
    """
    print('{}\n{}\r\n{}\r\n\r\n{}'.format(
        '-----------START-----------',
        req.method + ' ' + req.url,
        '\r\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
        req.body,
    ))


def loadFile(path_to_file):
    # get file type
    pathSuffix = pathlib.Path(path_to_file).suffix

    if pathSuffix == '.txt':
        with open(path_to_file, 'r') as tokeniseFile:
            content = tokeniseFile.read()
            return content
    elif pathSuffix == '.pdf':
        tempText = ''
        reader = PdfReader(path_to_file)
        for i in reader.pages:
            tempText = tempText + i.extract_text()

        return tempText
    elif pathSuffix == '.docx':
        return getText(path_to_file)


def writeToHtml(html):
    path = os.path.abspath('temp.html')
    url = 'file://' + path

    with open(path, 'w') as file:
        file.write(str(html))
        file.close()

    webbrowser.open(url)


def output(str, newline=False):
    if newline:
        print(str, end='\n\n')
    else:
        print(str)


def tokenise(path_to_file):
    url = 'https://api.gptzero.me/v2/predict/text'
    header = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Api-Key': 'c919e416fcd04f18acc72372e722b3c6'
    }
    data = {
        'document': loadFile(path_to_file)
    }

    res = requests.post(url, headers=header, data=json.dumps(data))

    return res.text


def text_to_pdf(text, filename):
    a4_width_mm = 210
    pt_to_mm = 0.35
    fontsize_pt = 10
    fontsize_mm = fontsize_pt * pt_to_mm
    margin_bottom_mm = 10
    character_width_mm = 7 * pt_to_mm
    width_text = a4_width_mm / character_width_mm

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(True, margin=margin_bottom_mm)
    pdf.add_page()
    pdf.set_font(family='Courier', size=fontsize_pt)
    splitted = text.split('\n')

    for line in splitted:
        lines = textwrap.wrap(line, width_text)

        if len(lines) == 0:
            pdf.ln()

        for wrap in lines:
            pdf.cell(0, fontsize_mm, wrap, ln=1)

    pdf.output(filename, 'F')


def generateReport(path, reportTitle='FuckGPT'):
    # prep terminal
    if os.path.exists(path):
        pass
    else:
        print("ERROR> Invalid path.")
        exit(0)

    os.system('clear')
    init(strip=not sys.stdout.isatty())
    cprint(figlet_format(reportTitle, font='starwars'),
           'white', attrs=['bold'])
    print('Generating your results...')
    print(
        f'Report generated on {date.today().strftime("%B %d, %Y")} {datetime.now().strftime("%H:%M:%S")}')

    print('')

    # parse response
    response = tokenise(path)  # text doc
    data = json.loads(response)
    prettyJSON = json.dumps(data, indent=2)

    # write json to disk
    with open(os.getcwd() + '/returnData.json', 'w') as file:
        file.write(prettyJSON)

    # return response
    if round(data["documents"][0]["completely_generated_prob"]) == 1:
        output(
            f'{bcolors.FAIL}> Your document is likely to be written entirely by ChatGPT. {bcolors.ENDC}')
    elif round(data["documents"][0]["completely_generated_prob"]) == 0:
        output(
            f'{bcolors.OKBLUE}> Your document is likely to be written by a human. {bcolors.ENDC}')
    else:
        print("ERROR> Error occured while analyzing the results.")
        exit(0)

    sentences = []
    human_plex = []
    ai_plex = []

    for i in data["documents"][0]["sentences"]:
        sentences.append(i)

        if i["perplexity"] >= 1 and i["perplexity"] <= 10:
            human_plex.append(i)
        elif i["perplexity"] >= 1 and i["perplexity"] <= 10:
            ai_plex.append(i)

    output(
        f'{bcolors.OKGREEN}Average generated probability: {data["documents"][0]["average_generated_prob"]}{bcolors.ENDC}')
    output(
        f'{bcolors.OKGREEN}Completely generated probability: {data["documents"][0]["completely_generated_prob"]}{bcolors.ENDC}')
    output(
        f'{bcolors.OKGREEN}Overall burstiness: {data["documents"][0]["overall_burstiness"]}{bcolors.ENDC}')

    print('')

    output(bcolors.OKBLUE + f'> Here is the document:' +
           bcolors.ENDC, newline=False)
    output(bcolors.OKBLUE + loadFile(path) + bcolors.ENDC, newline=False)

    if len(ai_plex) != 0:
        print("")
        output(bcolors.FAIL +
               'These sentences are likely to be generated by AI:', newline=True)
        for i in ai_plex:
            print(bcolors.FAIL + "____________________________________")
            print(i["sentence"] + bcolors.ENDC, end='\n\n')
    elif len(human_plex) != 0:
        print("")
        output(bcolors.OKCYAN +
               'These sentences are likely to be written by a human:', newline=True)
        for i in human_plex:
            print(bcolors.OKCYAN + "____________________________________")
            print(i["sentence"] + bcolors.ENDC, end='\n\n')
    else:
        print("")

    output('> These are perplexity values ranging from all sentences:', newline=False)
    for i in sentences:
        if i["generated_prob"] == 1:
            print(f"{bcolors.FAIL}____________________________________{bcolors.ENDC}")
            output("{}Probability of generated: {}{}".format(
                bcolors.FAIL, i["generated_prob"], bcolors.ENDC), newline=False)
            output("{}Perplexity: {}{}".format(bcolors.FAIL,
                   i["perplexity"], bcolors.ENDC), newline=False)
            print("{}Sentence: {}{}".format(bcolors.FAIL,
                  i["sentence"], bcolors.ENDC), end='\n\n')
        else:
            print(
                f"{bcolors.WARNING}____________________________________{bcolors.ENDC}")
            output("{}Probability of generated: {}{}".format(
                bcolors.WARNING, i["generated_prob"], bcolors.ENDC), newline=False)
            output("{}Perplexity: {}{}".format(bcolors.WARNING,
                   i["perplexity"], bcolors.ENDC), newline=False)
            print("{}Sentence: {}{}".format(bcolors.WARNING,
                  i["sentence"], bcolors.ENDC), end='\n\n')

    stop_words = stopwords.words('english')
    sentences = read_article(path)
    sentence_similarity_martix = build_similarity_matrix(sentences, stop_words)
    sentence_similarity_graph = nx.from_numpy_array(sentence_similarity_martix)
    scores = nx.pagerank(sentence_similarity_graph)

    ranked_sentence = sorted(((scores[i], s) for i, s in enumerate(sentences)), reverse=True)
    rankedLen = len(ranked_sentence)

    summary = generate_summary(path, rankedLen)
    
    output('> Here is the paraphrased text:', newline=False)
    print(summary)

    if sys.stdout != orig_stdout:
        sys.stdout.close()
        sys.stdout = orig_stdout
    else:
        pass


def login(username, password):
    connection = establishSqliteConnection(os.path.join(BASE_DIR, 'users.db'))
    cursor = connection.cursor()
    command = f"SELECT * FROM \"users\""
    cursor.execute(command)

    rows = cursor.fetchall()

    databaseUsername = ''
    databasePasswordHashed = ''
    databaseEmailActivate = 0

    for i in rows:
        if i[1] == username:
            databaseUsername = i[1]
            databasePasswordHashed = i[2]
            databaseEmailActivate = i[4]

    returnValues = {
        'username': databaseUsername,
        'password': password,
        'passwordHashed': databasePasswordHashed,
        'validCredencials': check_password_hash(databasePasswordHashed, password),
        'emailVerified': True if databaseEmailActivate == 1 else False
    }

    dateStr = f'{date.today().strftime("%B %d, %Y")} {datetime.now().strftime("%H:%M:%S")}'

    if check_password_hash(databasePasswordHashed, password) == True:
        command = f'''
UPDATE "users" SET date = '{dateStr}' WHERE username='{databaseUsername}'
        '''
        connection.execute(command)

    return returnValues

# feed web pages
@app.route('/')
def feedTemplate():
    user_agent = request.headers.get('User-Agent')
    user_agent = user_agent.lower()

    if 'iphone' in user_agent or 'android' in user_agent or 'ipad' in user_agent:
        return render_template('/phone.html')
    else:
        return render_template('/index.html')

@app.route('/paraphraser')
def feedParaphraser():
    user_agent = request.headers.get('User-Agent')
    user_agent = user_agent.lower()

    if 'iphone' in user_agent or 'android' in user_agent or 'ipad' in user_agent:
        return 'Paraphraser is currently not supported for mobile. Please access https://fuckgpt.herokuapp.com/paraphraser on a computer.'
    else:
        return render_template('/paraphraser.html')

@app.route('/teacher')
def feedTeacherTemplate():
    user_agent = request.headers.get('User-Agent')
    user_agent = user_agent.lower()

    if 'iphone' in user_agent or 'android' in user_agent or 'ipad' in user_agent:
        return render_template('/phone.html')
    else:
        return render_template('/index_teacher.html')

@app.route('/login', methods=['GET', 'POST'])
def loginUser():
    username = request.args.get('username')
    password = request.args.get('pass')

    if username is not None:
        credencials = login(username, password)

        return jsonify(credencials) # :UPDATE [account info page] Return account info page with render_template
    else:
        user_agent = request.headers.get('User-Agent')
        user_agent = user_agent.lower()

        if 'iphone' in user_agent or 'android' in user_agent or 'ipad' in user_agent:
            return '<html><body onload="alert("Login currently not supported on mobile devices.");"></body></html>'
        else:
            return render_template('/login.html')

@app.route('/verify')
def feedVerifyEmail():
    username = request.args.get('username')
    email = request.args.get('email')

    return render_template('email.html', link=f'/verifyEmail?username={username}&email={email}', username=username)

# bypass
@app.route('/c7f8f77fe951231edc4ac876a17f3b9d.txt')
def wechatBypass():
    return send_file(os.path.join(os.getcwd() + '/c7f8f77fe951231edc4ac876a17f3b9d.txt'), download_name='c7f8f77fe951231edc4ac876a17f3b9d.txt')


@app.route('/ads.txt')
def adsenseBypass():
    return send_file(os.path.join(os.getcwd() + '/ads.txt'), download_name='ads.txt')

# forms
@app.route('/', methods=['GET', 'POST'])
def file_upload():
    uploaded_file = request.files['files']

    try:
        if uploaded_file and allowed_file(uploaded_file.filename):
            if uploaded_file.filename != '':
                filename = secure_filename(uploaded_file.filename)
                fileExtension = pathlib.Path(filename).suffix
                if fileExtension == '.txt' or fileExtension == '.pdf' or fileExtension == '.docx':
                    os.makedirs(os.path.join(os.getcwd(), 'saved'), exist_ok=True)
                    uploaded_file.save(os.path.join('saved', secure_filename(uploaded_file.filename)))
                    with open(os.path.join(os.getcwd(), 'saved', 'report.txt'), 'w') as report:
                        orig_stdout = sys.stdout
                        sys.stdout = report
                        try:
                            generateReport(os.path.join(os.getcwd(), 'saved', secure_filename(uploaded_file.filename)))
                        except:
                            pass

                    with open(os.path.join(os.getcwd(), 'saved', 'report.txt'), 'r') as readerFile:
                        text = readerFile.read()
                        readerFile.close()

                    text_to_pdf(text.encode('latin-1', 'replace').decode('latin-1'), os.path.join(os.getcwd(), 'saved', 'report.pdf'))
                    removeDir = ['report.txt', secure_filename(
                        uploaded_file.filename)]
                    for i in removeDir:
                        os.remove(os.path.join(os.getcwd(), 'saved', i))

                    return send_file(os.path.join(os.getcwd(), 'saved', 'report.pdf'))
        else:
            return '''<html><body onload="alert('Invalid file extension. Only supports .txt, .pdf'); window.location.href='/';"></body></html>'''
    except Exception as e:
        return send_file(os.path.join(os.getcwd(), 'saved', 'report.pdf'))

    return redirect(url_for('feedTemplate'))


@app.route('/teacher', methods=['GET', 'POST'])
def file_upload_teacher():
    uploaded_file = request.files['files']

    try:
        if uploaded_file and allowed_file(uploaded_file.filename):
            if uploaded_file.filename != '':
                filename = secure_filename(uploaded_file.filename)
                fileExtension = pathlib.Path(filename).suffix
                if fileExtension == '.txt' or fileExtension == '.pdf' or fileExtension == '.docx':
                    os.makedirs(os.path.join(os.getcwd(), 'saved'), exist_ok=True)
                    uploaded_file.save(os.path.join('saved', secure_filename(uploaded_file.filename)))
                    with open(os.path.join(os.getcwd(), 'saved', 'report.txt'), 'w') as report:
                        orig_stdout = sys.stdout
                        sys.stdout = report
                        try:
                            generateReport(os.path.join(os.getcwd(), 'saved', secure_filename(uploaded_file.filename)))
                        except:
                            pass

                    with open(os.path.join(os.getcwd(), 'saved', 'report.txt'), 'r') as readerFile:
                        text = readerFile.read()
                        readerFile.close()

                    text_to_pdf(text.encode('latin-1', 'replace').decode('latin-1'),
                                os.path.join(os.getcwd(), 'saved', 'report.pdf'))
                    removeDir = ['report.txt', secure_filename(
                        uploaded_file.filename)]
                    for i in removeDir:
                        os.remove(os.path.join(os.getcwd(), 'saved', i))

                    return send_file(os.path.join(os.getcwd(), 'saved', 'report.pdf'))
        else:
            return '''<html><body onload="alert('Invalid file extension. Only supports .txt, .pdf'); window.location.href='/';"></body></html>'''
    except Exception as e:
        return send_file(os.path.join(os.getcwd(), 'saved', 'report.pdf'))

    return redirect(url_for('feedTeacherTemplate'))


@app.route('/paraphraser', methods=['GET', 'POST'])
def paraphraser():
    uploaded_file = request.files['files']
    
    try:
        if uploaded_file and allowed_file(uploaded_file.filename):
            if uploaded_file.filename != '':
                os.makedirs(os.path.join(os.getcwd(), 'saved'), exist_ok=True)
                uploaded_file.save(os.path.join(os.getcwd(), 'saved', secure_filename(uploaded_file.filename)))

                stop_words = stopwords.words('english')
                sentences = read_article(os.path.join(os.getcwd(), 'saved', secure_filename(uploaded_file.filename)))
                sentence_similarity_martix = build_similarity_matrix(sentences, stop_words)
                sentence_similarity_graph = nx.from_numpy_array(sentence_similarity_martix)
                scores = nx.pagerank(sentence_similarity_graph)

                ranked_sentence = sorted(((scores[i], s) for i, s in enumerate(sentences)), reverse=True)
                rankedLen = len(ranked_sentence)

                presummary = generate_summary(os.path.join(os.getcwd(), 'saved', secure_filename(uploaded_file.filename)), rankedLen)

                stop_words = stopwords.words('english')
                summarize_text = []
                sentences = presummary
                sentence_similarity_martix = build_similarity_matrix(sentences, stop_words)
                sentence_similarity_graph = nx.from_numpy_array(sentence_similarity_martix)
                scores = nx.pagerank(sentence_similarity_graph)

                ranked_sentence = sorted(((scores[i], s) for i, s in enumerate(sentences)), reverse=True)

                for i in range(rankedLen):
                    summarize_text.append(" ".join(ranked_sentence[i][1]))

                summary = '. '.join(summarize_text)
                
                with open(os.path.join(os.getcwd(), 'saved', 'paraphrase.txt'), 'w') as report:
                    orig_stdout = sys.stdout
                    sys.stdout = report

                    cprint(figlet_format('FuckGPT', font='starwars'), 'white', attrs=['bold'])
                    print('Generating your results...')
                    print(f'Report generated on {date.today().strftime("%B %d, %Y")} {datetime.now().strftime("%H:%M:%S")}')

                    print('')

                    with open(os.path.join(os.getcwd(), 'saved', 'paraphrase.txt'), 'w') as report:
                        print("> Below is the paraphrased summary of the text:")    
                        print(summary)

                    if sys.stdout != orig_stdout:
                        sys.stdout.close()
                        sys.stdout = orig_stdout
                    else:
                        pass

                    with open(os.path.join(os.getcwd(), 'saved', 'paraphrase.txt'), 'r') as readerFile:
                        text = readerFile.read()
                        
                    text_to_pdf(text.encode('latin-1', 'replace').decode('latin-1'),
                                os.path.join(os.getcwd(), 'saved', 'paraphrase.pdf'))
                    removeDir = ['paraphrase.txt', secure_filename(uploaded_file.filename)]
                    for i in removeDir:
                        os.remove(os.path.join(os.getcwd(), 'saved', i))

                    return send_file(os.path.join(os.getcwd(), 'saved', 'paraphrase.pdf'))
    except Exception as e:
        return send_file(os.path.join(os.getcwd(), 'saved', 'paraphrase.pdf'))

    return redirect(url_for('feedParaphraser'))


@app.route('/create', methods=['GET', "POST"])
def createUser():
    connection = establishSqliteConnection(
        os.path.join(os.getcwd(), 'users.db'))
    connection.execute(table_connection)

    username = request.args.get('username')
    password = request.args.get('pass')
    email = request.args.get('email')

    if username is not None and password is not None:
        passwordHashed = generate_password_hash(password)
        dateStr = f'{date.today().strftime("%B %d, %Y")} {datetime.now().strftime("%H:%M:%S")}'

        command = f'''
    INSERT INTO "users" (id, username, passwordhashed, email, emailVerified, date)
    VALUES ('{str(uuid.uuid4())}', '{username}', '{passwordHashed}', '{email}', 0, '{dateStr}')
            '''

        connection.execute(command)
        connection.commit()
        connection.close()

        if email == None:
            return f'Failed to create account. Received email: {email}'
        else:
            print('send email verification')
            emailData = f'''<a href="https://fuckgpt.herokuapp.com/verify?username={username}&email={email}">Hey -username-, Click here to verify your email.</a>'''
            email = sendEmail(email, 'Account Verification', emailData)

            return 'Account created. Please verify your account with the link sent to your inbox to activate your account. This page will redirect in 5 seconds. <body onload="setTimeout(() => {window.location.href=\'/login?username=%s&pass=%s\'}, 5000)"></body>' % (username, password)
    else:
        user_agent = request.headers.get('User-Agent')
        user_agent = user_agent.lower()

        if 'iphone' in user_agent or 'android' in user_agent or 'ipad' in user_agent:
            return '<html><body onload="alert("Login currently not supported on mobile devices.");"></body></html>'
        else:
            return render_template('/createAccount.html')


@app.route('/verifyEmail', methods=['GET', 'POST'])
def verifyEmail():
    username = request.args.get('username')
    email = request.args.get('email')

    connection = establishSqliteConnection(os.path.join(BASE_DIR, 'users.db'))
    cursor = connection.cursor()
    command = f"SELECT * FROM \"users\""
    cursor.execute(command)

    rows = cursor.fetchall()

    databaseUsername = ''
    databaseEmail = ''

    for i in rows:
        if i[1] == username and i[3] == email:
            databaseUsername = i[1]
            databaseEmail = i[3]
            dateStr = f'{date.today().strftime("%B %d, %Y")} {datetime.now().strftime("%H:%M:%S")}'

            connection.executescript(command)
            connection.execute(
                f'''UPDATE "users" SET date = '{dateStr}' WHERE username='{databaseUsername}\'''')
            connection.execute(
                f'''UPDATE "users" SET emailVerified = 1 WHERE username='{databaseUsername}\'''')
            connection.execute(
                f'''UPDATE "users" SET email = '{databaseEmail}' WHERE username='{databaseUsername}\'''')

            return '<body onload="alert(\'Email verified!\'); window.history.go(-1); return false;"></body>'
        else:
            return '<body onload="alert(\'Failed to verify email. Please try again later.\'); window.history.go(-1); return false;"></body>'


if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', 0))
    port = sock.getsockname()[1]
    sock.close()
    app.run(debug=True, port=2350)