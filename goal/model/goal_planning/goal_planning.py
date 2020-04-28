import torch
from tqdm import tqdm

from goal.model.goal_finish.lstm import RNN
from goal.model.goal_finish.config import Config as FinishConfig
from goal.model.goal_planning.config import Config
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
                text = torch.tensor(text, dtype=torch.long).unsqueeze(1) # (seq_len, batch)
                first_goal = torch.tensor(first_goal, dtype=torch.long).unsqueeze(0) # (batch, seq_len)
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
            return output

    def goal_entity_infer(self, past_entity_seq, cur_entity, final_entity):
        self.goal_entity.eval()
        with torch.no_grad():
            past_entity_seq = torch.tensor(past_entity_seq, dtype=torch.long).unsqueeze(1)
            cur_entity = torch.tensor(cur_entity, dtype=torch.long).unsqueeze(0)
            final_entity = torch.tensor(final_entity, dtype=torch.long).unsqueeze(0)
            output = self.goal_entity(past_entity_seq, cur_entity, final_entity, "test")
            return output


def file_reader(file_path):
    with open(file_path, "r", encoding='utf-8') as f:
        data = eval(f.read())
    return data


def read_goal_finish_data(tag):
    path_prefix = "../../data/train/"
    utterance = file_reader(path_prefix + tag + "_binary_utterance.txt")
    goal_type = file_reader(path_prefix + tag + "_binary_goal_type.txt")
    final_goal_type = file_reader(path_prefix + tag + "_final_goal_type.txt")
    return {
        'utterance': utterance,
        'goal_type': goal_type,
        'final_goal_type': final_goal_type
    }


def read_goal_type_data(tag):
    path_prefix = "../../data/train/"
    past_goal_type_seq = file_reader(path_prefix + tag + "_next_goal_type.txt")
    final_goal_type = file_reader(path_prefix + tag + "_final_goal_type.txt")
    return {
        'past_goal_type_seq': past_goal_type_seq,
        'final_goal_type': final_goal_type
    }


def read_goal_entity_data(tag):
    path_prefix = "../../data/train/"
    past_goal_entity_seq = file_reader(path_prefix + tag + "_next_goal_entity.txt")
    final_goal_entity = file_reader(path_prefix + tag + "_final_goal_entity.txt")
    return {
        'past_goal_entity_seq': past_goal_entity_seq,
        'final_goal_entity': final_goal_entity
    }


def main(config, tag):
    goal_planning = GoalPlanning(config)
    goal_finish_data, goal_type_data, goal_entity_data = read_goal_finish_data(tag), read_goal_type_data(
        tag), read_goal_entity_data(tag)
    if tag == "test":
        round_ids, max_ids = file_reader("../../data/train/test_round_id.txt"), file_reader("../../data/train/test_max_id.txt")
    total_cnt = len(goal_finish_data['goal_type'])
    print(tag + ' data size:', total_cnt)

    goal_type_dict = file_reader("../../data/others/goal_type_dict.txt")
    goal_entity_dict = file_reader("../../data/others/goal_entity_dict.txt")
    type_idx = list(goal_type_dict.keys())
    entity_idx = list(goal_entity_dict.keys())

    if tag == "test":
        next_goal_types, next_goal_entitys, goal_finishs = list(), list(), list()
        for idx in tqdm(range(total_cnt)):
            cur_id = round_ids[idx]

            if cur_id == 1 or cur_id == max_ids[idx] - 2:
                cur_utterance = goal_finish_data['utterance'][idx]
                cur_goal_type = goal_finish_data['goal_type'][idx]
                final_goal_type = goal_finish_data['final_goal_type'][idx]
                goal_finish = goal_planning.goal_finish_infer(cur_utterance, cur_goal_type, final_goal_type)
                if goal_finish == 1:
                    cur_id += 1
                    goal_finishs.append(1)
                else:
                    goal_finishs.append(0)
            else:
                goal_finishs.append(0)

            if cur_id == 1:
                next_goal_type = goal_type_data['past_goal_type_seq'][idx][0][0]
                next_goal_entity = goal_entity_data['past_goal_entity_seq'][idx][0][0]
            elif cur_id == max_ids[idx] - 1:
                next_goal_type = goal_type_data['final_goal_type'][idx]
                next_goal_entity = goal_entity_data['final_goal_entity'][idx]
            elif cur_id >= max_ids[idx]:
                next_goal_types.append("再见")
                next_goal_entitys.append("再见")
                continue
            else:
                next_goal_type, next_goal_type_prob = None, 0
                final_goal = goal_type_data['final_goal_type'][idx]
                for past_goal_type_seq in goal_type_data['past_goal_type_seq'][idx]:
                    cur_goal = past_goal_type_seq[-1]
                    prob = goal_planning.goal_type_infer(past_goal_type_seq, cur_goal, final_goal)

                    if prob > next_goal_type_prob:
                        next_goal_type_prob = prob
                        next_goal_type = cur_goal

                next_goal_entity, next_goal_entity_prob = None, 0
                final_goal_entity = goal_entity_data['final_goal_entity'][idx]
                for past_goal_entity_seq in goal_entity_data['past_goal_entity_seq'][idx]:
                    cur_goal_entity = past_goal_entity_seq[-1]
                    prob = goal_planning.goal_entity_infer(past_goal_entity_seq, cur_goal_entity, final_goal_entity)

                    if prob > next_goal_entity_prob:
                        next_goal_entity_prob = prob
                        next_goal_entity = cur_goal_entity

            next_goal_types.append(type_idx[next_goal_type])
            next_goal_entitys.append(entity_idx[next_goal_entity])

    else:
        next_goal_types, next_goal_entitys = list(), list()
        for idx in tqdm(range(total_cnt)):
            cur_utterance = goal_finish_data['utterance'][idx]
            cur_goal_type = goal_finish_data['goal_type'][idx]
            goal_finish = goal_planning.goal_finish_infer(cur_utterance, cur_goal_type)

            if goal_finish == 0:
                if goal_type_data['past_goal_type_seq'][idx][-2] == goal_type_data['past_goal_type_seq'][idx][-1]:
                    next_goal_types.append(1)
                else:
                    next_goal_types.append(0)
                if goal_entity_data['past_goal_entity_seq'][idx][-2] == goal_entity_data['past_goal_entity_seq'][idx][-1]:
                    next_goal_entitys.append(1)
                else:
                    next_goal_entitys.append(0)

            else:
                past_goal_type_seq = goal_type_data['past_goal_type_seq'][idx]
                cur_goal = past_goal_type_seq[-1]
                final_goal = goal_type_data['final_goal_type'][idx]
                prob = goal_planning.goal_type_infer(past_goal_type_seq, cur_goal, final_goal)
                if prob > 0.5:
                    next_goal_types.append(1)
                else:
                    next_goal_types.append(0)

                past_goal_entity_seq = goal_entity_data['past_goal_entity_seq'][idx]
                cur_goal_entity = past_goal_entity_seq[-1]
                final_goal_entity = goal_entity_data['final_goal_entity'][idx]
                prob = goal_planning.goal_entity_infer(past_goal_entity_seq, cur_goal_entity, final_goal_entity)
                if prob > 0.5:
                    next_goal_entitys.append(1)
                else:
                    next_goal_entitys.append(0)

    if tag == "test":
        next_goal = list(zip(next_goal_types, next_goal_entitys, goal_finishs))
        with open('../../output/next_goal.txt', 'w', encoding='utf-8') as f:
            f.write(str(next_goal))
    else:
        next_goal_type_label = file_reader("../../data/train/" + tag + "_next_goal_type_label.txt")
        next_goal_entity_label = file_reader("../../data/train/" + tag + "_next_goal_entity_label.txt")

        true_type = 0
        for i in range(len(next_goal_types)):
            true_type += (next_goal_types[i] == next_goal_type_label[i])
        print("type acc:", true_type / len(next_goal_types))
        true_entity = 0
        for i in range(len(next_goal_entitys)):
            true_entity += (next_goal_entitys[i] == next_goal_entity_label[i])
        print("entity acc:", true_entity / len(next_goal_entitys))


if __name__ == '__main__':
    config = Config()
    main(config, "test")
