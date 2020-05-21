import re

import torch

from goal.model.goal_finish.lstm import RNN
from goal.model.goal_finish.config import Config as FinishConfig
from goal.model.next_goal_entity.astar import AStarEntity
from goal.model.next_goal_entity.config import Config as EntityConfig
from goal.model.next_goal_type.astar import AStarType
from goal.model.next_goal_type.config import Config as TypeConfig


class GoalPlanning:
    def __init__(self, config):
        self.goal_finish = RNN(FinishConfig())
        self.goal_type = AStarType(TypeConfig())
        self.goal_entity = AStarEntity(EntityConfig())

        self.goal_finish.load_state_dict(torch.load(config.goal_finish_path, map_location=torch.device('cpu')))
        self.goal_type.load_state_dict(torch.load(config.goal_type_path, map_location=torch.device('cpu')))
        self.goal_entity.load_state_dict(torch.load(config.goal_entity_path, map_location=torch.device('cpu')))

    def goal_finish_infer(self, text, first_goal, final_goal):
        self.goal_finish.eval()
        with torch.no_grad():
            if len(text) > 0:
                text = torch.tensor(text, dtype=torch.long).unsqueeze(1)  # (seq_len, batch)
                first_goal = torch.tensor(first_goal, dtype=torch.long).unsqueeze(0)  # (batch, seq_len)
                final_goal = torch.tensor(final_goal, dtype=torch.long).unsqueeze(0)
                output = self.goal_finish(text, first_goal, final_goal, "test")
                pred = output.argmax(dim=-1)
                return pred.item()
            else:
                return 0

    def goal_type_infer(self, past_goal_type_seq, cur_goal_type, final_goal_type):
        self.goal_type.eval()
        with torch.no_grad():
            past_goal_type_seq = torch.tensor(past_goal_type_seq, dtype=torch.long).unsqueeze(1)
            cur_goal_type = torch.tensor(cur_goal_type, dtype=torch.long).unsqueeze(0)
            final_goal_type = torch.tensor(final_goal_type, dtype=torch.long).unsqueeze(0)
            # print(final_goal_type)
            # print(past_goal_type_seq.shape, cur_goal_type.shape, final_goal_type.shape)
            output = self.goal_type(past_goal_type_seq, cur_goal_type, final_goal_type, "test")
            return output.item()

    def goal_entity_infer(self, past_entity_seq, cur_entity, final_entity):
        self.goal_entity.eval()
        with torch.no_grad():
            past_entity_seq = torch.tensor(past_entity_seq, dtype=torch.long).unsqueeze(1)
            cur_entity = torch.tensor(cur_entity, dtype=torch.long).unsqueeze(0)
            final_entity = torch.tensor(final_entity, dtype=torch.long).unsqueeze(0)
            output = self.goal_entity(past_entity_seq, cur_entity, final_entity, "test")
            return output.item()


def file_reader(file_path):
    with open(file_path, "r", encoding='utf-8') as f:
        data = eval(f.read())
    return data


def remove_punctuation(line):
    line = re.sub(r"\[\d*\]", "", line)
    return re.sub(r'[^\u4e00-\u9fa5^a-z^A-Z^0-9]', '', line)


def word_replace(word):
    word = word.replace(' ', '').replace('\n', '')
    word = word.replace("问User", "问用户").replace("poi推荐", "兴趣点推荐").replace("的新闻", "新闻")
    word = word.replace("说A好的幸福呢", "说好的幸福呢")
    word = remove_punctuation(word)
    return word


def infer(line, config):
    goal_planning = GoalPlanning(config)
    other_prefix = "./others/"
    word_dict = file_reader(other_prefix + "word_dict.txt")
    UNK = word_dict["UNK"]
    goal_type_dict = file_reader(other_prefix + "goal_type_dict.txt")
    goal_entity_dict = file_reader(other_prefix + "goal_entity_dict.txt")
    type_nb_dict = file_reader(other_prefix + "goal_type_neighbour.txt")
    entity_nb_dict = file_reader(other_prefix + "goal_entity_neighbour.txt")
    idx2word = list(word_dict.keys())
    idx2type = list(goal_type_dict.keys())
    idx2entity = list(goal_entity_dict.keys())

    entity_same_as_type = ["再见", "问天气", "问时间", "天气信息推送", '问用户爱好', '问用户年龄', '问用户性别', '问用户姓名']

    last_session_id, last_round_id, session_type_seq, session_entity_seq = -1, 0, [], []
    goal_finishes, next_types, next_entitys, session_id, round_ids = [], [], [], [], []


