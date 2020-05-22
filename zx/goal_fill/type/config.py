import torch
import os


class Config:
    def __init__(self):
        self.output_size = 1
        self.embed_size = 64
        self.hidden_size = 256
        self.n_layers = 1
        self.bidirectional = True
        self.dropout_probability = 0
        self.shuffle = True
        self.batch_size = 128
        self.lr = 1e-5
        self.max_norm = 1
        self.num_epoch = 50
        # self.device = torch.device("cpu")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.save_path = "next_goal_type.pt"

        with open('goal_fill/others/word_dict.txt', 'r', encoding='utf-8') as f:
            self.word_dict = eval(f.read())

        # print(os.getcwd())
        with open('goal_fill/type/goal_type_dict.txt', 'r', encoding='utf-8') as f:
            self.goal_type_size = len(eval(f.read()))

if __name__ == '__main__':
    type_dict = open('./goal_type_dict.txt', 'r', encoding='utf-8')