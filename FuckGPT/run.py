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
import argparse
from PyPDF2 import PdfReader, PdfFileReader
import pathlib
import matplotlib.pyplot as plt

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
    
def output(str, newline=False, fastOutput=False):
    if fastOutput:
        if newline:
            for char in str:
                sleep(randint(1, 3) / 250)
                sys.stdout.write(char)
                sys.stdout.flush()

            print("\n\n")
        else:
            for char in str:
                sleep(randint(1, 3) / 250)
                sys.stdout.write(char)
                sys.stdout.flush()

            print("\n")
    else:
        if newline:
            for char in str:
                sleep(randint(1, 5) / 100)
                sys.stdout.write(char)
                sys.stdout.flush()

            print("\n\n")
        else:
            for char in str:
                sleep(randint(1, 5) / 100)
                sys.stdout.write(char)
                sys.stdout.flush()

            print("\n")

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

if __name__ == '__main__':
    # prep
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', type=str, required=True, help='Path to the txt file to tokenise.')
    args = parser.parse_args()

    # prep terminal
    if os.path.exists(args.path):
        pass
    else:
        print("ERROR> Invalid path.")
        exit(0)

    os.system('clear')
    init(strip=not sys.stdout.isatty())
    cprint(figlet_format('FuckGPT', font='starwars'), 'white', attrs=['bold'])
    for i in range(randint(2, 6)):
        for i in range(5):
            sys.stdout.write('\rGenerating your results' + ( '.' * i ) + ' ')
            sys.stdout.flush()
            time.sleep(0.5)

    print('')

    # parse response
    response = tokenise(args.path) # text doc
    data = json.loads(response)
    prettyJSON = json.dumps(data, indent=2)

    # write json to disk
    with open(os.getcwd() + '/returnData.json', 'w') as file:
        file.write(prettyJSON)

    # return response
    os.system("clear")
    cprint(figlet_format('FuckGPT', font='starwars'), 'white', attrs=['bold'])
    if round(data["documents"][0]["average_generated_prob"]) == 1:
        output(f'{bcolors.FAIL} > Your document is likely to be written entirely by ChatGPT. {bcolors.ENDC}')
    elif round(data["documents"][0]["average_generated_prob"]) == 0:
        output(f'{bcolors.OKBLUE} > Your document is likely to be written by a human. {bcolors.ENDC}')
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

    print("")

    output(f'{bcolors.OKGREEN} Average generated probability: {data["documents"][0]["average_generated_prob"]}{bcolors.ENDC}')
    output(f'{bcolors.OKGREEN} Completely generated probability: {data["documents"][0]["completely_generated_prob"]}{bcolors.ENDC}')
    output(f'{bcolors.OKGREEN} Overall burstiness: {data["documents"][0]["overall_burstiness"]}{bcolors.ENDC}')

    print('')

    output(bcolors.OKBLUE +  f'> Here is the document:', newline=False)
    output(loadFile(args.path) + bcolors.ENDC, fastOutput=True)

    if len(ai_plex) != 0:
        output(bcolors.FAIL + 'These sentences are likely to be generated by AI:', newline=True)
        for i in ai_plex:
            print(bcolors.FAIL + "____________________________________")
            print(i["sentence"] + bcolors.ENDC, end='\n\n')
    elif len(human_plex) != 0:
        output(bcolors.OKCYAN + 'These sentences are likely to be written by a human:', newline=True)
        for i in human_plex:
            print(bcolors.OKCYAN + "____________________________________")
            print(i["sentence"] + bcolors.ENDC, end='\n\n')

    print("")

    output('These are perplexity values ranging from all sentences:', newline=True)
    for i in sentences:
        if i["generated_prob"] == 1:
            print(f"{bcolors.FAIL}____________________________________{bcolors.ENDC}")
            output("{} Probability of generated: {}{}".format(bcolors.FAIL, i["generated_prob"], bcolors.ENDC), newline=False)
            output("{} Perplexity: {}{}".format(bcolors.FAIL, i["perplexity"], bcolors.ENDC), newline=False)
            print("{} Sentence: {}{}".format(bcolors.FAIL, i["sentence"], bcolors.ENDC), end='\n\n')
        else:
            print(f"{bcolors.WARNING}____________________________________{bcolors.ENDC}")
            output("{} Probability of generated: {}{}".format(bcolors.WARNING, i["generated_prob"], bcolors.ENDC), newline=False)
            output("{} Perplexity: {}{}".format(bcolors.WARNING, i["perplexity"], bcolors.ENDC), newline=False)
            print("{} Sentence: {}{}".format(bcolors.WARNING, i["sentence"], bcolors.ENDC), end='\n\n')

    # plot chart
    x = []
    y = []
    count = 0

    # prepare data
    for i in data["documents"][0]["paragraphs"]:
        y.append(i["completely_generated_prob"])
        count += 1
        x.append(count)

    

    plt.plot(x, y)
    plt.xlabel('Sentence #')
    plt.ylabel('Generated Probability')
    plt.savefig('generated_prob.png')
    plt.show()