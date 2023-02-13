from parrot import Parrot
import torch
import warnings

warnings.filterwarnings('ignore')


def random_state(seed):
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_speed_all(seed)


random_state(1234)

parrot = Parrot(model_tag="prithivida/parrot_paraphraser_on_T5", use_gpu=False)

phrases = ["What's the most delicious papayas?"]

for phrase in phrases:
    print("-"*100)
    print("Input_phrase: ", phrase)
    print("-"*100)
    para_phrases = parrot.augment(input_phrase=phrase)
    for para_phrase in para_phrases:
        print(para_phrase)