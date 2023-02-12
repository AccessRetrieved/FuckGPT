from flask import Flask, render_template, request, url_for, redirect, send_file
from werkzeug.utils import secure_filename
import os
import pathlib
import requests
import webbrowser
import os
import json
from time import sleep
import time
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

# init
app = Flask(__name__)
allowedExtensions = {'txt', 'pdf'}


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


def allowed_file(fileExt):
    return '.' in fileExt and fileExt.rsplit('.', 1)[1].lower() in allowedExtensions


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

        print(tempText)
        return tempText


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
        'Content-Type': 'application/json'
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


def generateReport(path):
    # prep terminal
    if os.path.exists(path):
        pass
    else:
        print("ERROR> Invalid path.")
        exit(0)

    os.system('clear')
    init(strip=not sys.stdout.isatty())
    cprint(figlet_format('FuckGPT', font='starwars'), 'white', attrs=['bold'])
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
    if round(data["documents"][0]["average_generated_prob"]) == 1:
        output(
            f'{bcolors.FAIL}> Your document is likely to be written entirely by ChatGPT. {bcolors.ENDC}')
    elif round(data["documents"][0]["average_generated_prob"]) == 0:
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

    # print("")

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

# web pages


@app.route('/')
def feedTemplate():
    return render_template('/index.html')


@app.route('/', methods=['GET', 'POST'])
def file_upload():
    uploaded_file = request.files['files']

    try:
        if uploaded_file and allowed_file(uploaded_file.filename):
            if uploaded_file.filename != '':
                filename = secure_filename(uploaded_file.filename)
                fileExtension = pathlib.Path(filename).suffix
                if fileExtension == '.txt' or fileExtension == '.pdf':
                    os.makedirs(os.path.join(
                        os.getcwd(), 'saved'), exist_ok=True)
                    uploaded_file.save(os.path.join(
                        'saved', secure_filename(uploaded_file.filename)))
                    with open(os.path.join(os.getcwd(), 'saved', 'report.txt'), 'w') as report:
                        sys.stdout = report
                        generateReport(os.path.join(
                            os.getcwd(), 'saved', secure_filename(uploaded_file.filename)))

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
            return '''<html><body onload="alert('Invalid file extension. Only supports .txt, .pdf'); window.location.href='http://127.0.0.1:5000/';"></body></html>'''
    except Exception as e:
        return send_file(os.path.join(os.getcwd(), 'saved', 'report.pdf'))
        print(e)
        return '''<html><body onload="alert('Error generating report. Please try again.'); window.location.href='http://127.0.0.1:5000/';"></body></html>'''

    return redirect(url_for('feedTemplate'))


if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', 0))
    port = sock.getsockname()[1]
    sock.close()
    app.run(debug=False, port=2350)
