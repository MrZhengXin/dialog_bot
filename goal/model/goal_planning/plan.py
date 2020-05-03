import re

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


def infer(config):
    goal_planning = GoalPlanning(config)
    other_prefix = "../../data/others/"
    word_dict = file_reader(other_prefix + "word_dict.txt")
    UNK = word_dict["UNK"]
    goal_type_dict = file_reader(other_prefix + "goal_type_dict.txt")
    goal_entity_dict = file_reader(other_prefix + "goal_entity_dict.txt")
    type_nb_dict = file_reader(other_prefix + "goal_type_neighbour.txt")
    entity_nb_dict = file_reader(other_prefix + "goal_entity_neighbour.txt")
    idx2word = list(word_dict.keys())
    idx2type = list(goal_type_dict.keys())
    idx2entity = list(goal_entity_dict.keys())

    stars = file_reader("../../data/others/all_star.txt")
    mvs = file_reader("../../data/others/all_movie.txt")
    songs = file_reader("../../data/others/all_song.txt")
    pois = file_reader("../../data/others/all_poi.txt")
    foods = file_reader("../../data/others/all_food.txt")
    entity_same_as_type = ["再见", "问天气", "问时间", "天气信息推送", '问用户爱好', '问用户年龄', '问用户性别', '问用户姓名']

    last_session_id, last_round_id, session_type_seq, session_entity_seq = -1, 0, [], []
    goal_finishes, next_types, next_entitys, session_id, round_ids = [], [], [], [], []

    goal_finish_debug = open("../../output/goal_finish_debug.txt", 'w', encoding='utf-8')
    goal_type_debug = open("../../output/goal_type_debug.txt", 'w', encoding='utf-8')
    goal_entity_debug = open("../../output/goal_entity_debug.txt", 'w', encoding='utf-8')

    with open("../../data/process/test.txt", "r", encoding='utf-8') as f:
        cnt = 0
        for line in tqdm(f.readlines()):
            cnt += 1
            if line == "\n":
                continue
            line = line.split('\t')

            cur_session_id = int(line[0])
            session_id.append(cur_session_id)

            utt_lst = line[1].split("\001")
            first_round_flag = False
            if len(utt_lst) <= 1:
                first_round_flag = True
            utt = ' '.join(utt_lst)
            round_id = re.findall(r"\[(\d*)\]", utt)
            round_id = list(map(int, round_id))
            if len(round_id) == 1:
                round_id = round_id[-1]
            elif len(round_id) > 1:
                if round_id[-1] == round_id[-2] + 1:
                    round_id = round_id[-1]
                elif round_id[-1] == round_id[-2]:
                    round_id = round_id[-1] + 1
                elif round_id[-1] > round_id[-2] + 1:
                    round_id = round_id[-2] + 1
                else:
                    raise ValueError
            else:
                round_id = 1
            max_round_id = int(line[-1].replace('\n', ''))
            if max_round_id < round_id:
                max_round_id = round_id

            utt = ' '.join(utt_lst[max(-2, -len(utt_lst)):])
            utt = re.sub("\[\d*\]", "", utt)
            utt = re.sub(
                r'[~`!#$%^&*()_+-=|\';":/.,?><~·！@#￥%……&*（）——+-=“：’；、。，？》《{}]+', "", utt)
            utt = [word_dict.get(word, UNK) for word in utt.strip().split() if word != ""]

            first_type_idx = goal_type_dict[word_replace(line[3])]
            first_entity_idx = goal_entity_dict[word_replace(line[4])]
            final_type_idx = goal_type_dict[word_replace(line[5])]
            final_entity_idx = goal_entity_dict[word_replace(line[6])]

            if cur_session_id != last_session_id:
                cur_type_idx = first_type_idx
                cur_entity_idx = first_entity_idx
                last_round_id = 0
            elif round_id >= last_round_id:
                cur_type_idx = session_type_seq[-1]
                cur_entity_idx = session_entity_seq[-1]
            elif round_id < last_round_id:
                last_round_id = round_id
                if len(session_type_seq) >= 2:
                    cur_type_idx = session_type_seq[-2]
                else:
                    cur_type_idx = session_type_seq[-1]
                if len(session_entity_seq) >= 2:
                    cur_entity_idx = session_entity_seq[-2]
                else:
                    cur_entity_idx = session_entity_seq[-1]

            # if cur_session_id == 1401:
            #     print()

            if round_id < max_round_id and first_round_flag == False:
                goal_finish = goal_planning.goal_finish_infer(utt, cur_type_idx, final_type_idx)
                if goal_finish == 1:
                    round_id += 1
                    goal_finishes.append(1)
                else:
                    goal_finishes.append(0)
                # if round_id < last_round_id:
                #     round_id = last_round_id
                # debug
                utt_word = ' '.join([idx2word[idx] for idx in utt])
                cur_type_name = idx2type[cur_type_idx]
                final_type_name = idx2type[final_type_idx]
                goal_finish_debug.write(str(cur_session_id) + '-' + str(
                    round_id) + ':' + str(goal_finish) + '\t' + utt_word + '\t' + cur_type_name + '\t' + final_type_name + '\n')
            else:
                goal_finishes.append(0)
            round_ids.append(round_id)

            if cur_session_id != last_session_id:
                # session_type_seq = [first_type_idx]
                # session_entity_seq = [first_entity_idx]
                session_type_seq = []
                session_entity_seq = []
            # if cur_session_id == last_session_id and round_id == last_round_id:
            #     if len(session_type_seq) > 1:
            #         session_type_seq = session_type_seq[:-1]
            #     if len(session_entity_seq) > 1:
            #         session_entity_seq = session_entity_seq[:-1]

            # if cur_session_id == 86:
            #     print()

            # if round_id == last_round_id:
            #     next_type = session_type_seq[-1]
            #     goal_type_debug.write(str(cur_session_id) + '-' + str(last_round_id) + ':' +
            #                           str(session_type_seq) + '\n')
            #     next_entity = session_entity_seq[-1]
            #     goal_entity_debug.write(str(cur_session_id) + '-' + str(last_round_id) + ':' +
            #                             str(session_type_seq) + '\n')
            # else:
            if round_id != last_round_id:
                if cur_session_id == 104 and round_id == 3:
                    print()
                user_profile = eval(line[8])
                kgs = eval(line[7])
                kg_entitys = []
                news, star, song, mv, food, poi = [], [], [], [], [], []
                # reject_song_flag = False
                # reject_song = []
                # demand_song_flag = False
                # if idx2type[session_type_seq[0]] == "音乐点播":
                #     demand_song_flag = True
                for kg in kgs:
                    for i in range(3):
                        kg[i] = word_replace(kg[i])
                        if kg[i] in goal_entity_dict.keys():
                            kg_entitys.append(kg[i])

                        if i in [0, 2]:
                            if kg[i] in stars:
                                star.append(kg[i])
                            elif kg[i] in songs:
                                song.append(kg[i])
                            elif kg[i] in mvs:
                                mv.append(kg[i])
                            elif kg[i] in foods:
                                food.append(kg[i])
                            elif kg[i] in pois:
                                poi.append(kg[i])

                        if i == 1 and kg[i] == "新闻":
                            news.append(kg[0] + "新闻")

                        # if i == 1 and kg[i] == "演唱":
                        #     reject_song_flag = True
                        #     reject_song.append(kg[2])

                kg_entitys = list(set(kg_entitys))
                news = list(set(news))
                star = list(set(star))
                # if demand_song_flag:
                #     for i in range(3):
                #         if kgs[i][2] not in ' '.join(utt_lst):
                #             song.append(kgs[i][2])
                # else:
                song = list(set(song))
                mv = list(set(mv))
                # if reject_song_flag == True:
                #     for i in range(1, last_round_id + 1):
                #         entity_name = idx2entity[session_entity_seq[i]]
                #         if entity_name in reject_song:
                #             reject_song.remove(entity_name)

                while last_round_id < round_id:
                    if last_round_id == 0:
                        next_type = first_type_idx
                        next_entity = first_entity_idx
                    elif last_round_id == max_round_id - 2:
                        next_type = final_type_idx
                        next_entity = final_entity_idx
                    elif last_round_id >= max_round_id - 1:
                        next_type = goal_type_dict["再见"]
                        next_entity = goal_entity_dict["再见"]
                    else:
                    # if cur_session_id == 30 and round_id == 3:
                    #     print()
                    # if cnt == 4893:
                    #     print()
                    # type
                        next_type, next_type_prob = None, 0
                        last_type_idx = session_type_seq[-1]
                        for type_nb in type_nb_dict[last_type_idx]:
                            if type_nb == last_type_idx and len(type_nb_dict[last_type_idx]) > 1:
                                continue
                            past_type_seq = session_type_seq + [type_nb]
                            prob = goal_planning.goal_type_infer(past_type_seq, type_nb, final_type_idx)
                            type_nb_name = idx2type[type_nb]
                            if len(news) == 0 and "新闻" in type_nb_name:
                                continue
                            if len(star) == 0 and "明星" in type_nb_name:
                                continue
                            if len(song) == 0 and "音乐" in type_nb_name:
                                continue
                            if len(mv) == 0 and "电影" in type_nb_name:
                                continue
                            if len(food) == 0 and "美食" in type_nb_name:
                                continue
                            if len(poi) == 0 and "兴趣点" in type_nb_name:
                                continue
                            if type_nb_name == "再见":
                                continue
                            # debug
                            past_type_seq_name = [idx2type[idx] for idx in past_type_seq]
                            type_nb_name = idx2type[type_nb]
                            final_type_name = idx2type[final_type_idx]
                            goal_type_debug.write(str(cur_session_id) + '-' + str(last_round_id) + ':' + str(prob) + '\t' + str(
                                past_type_seq_name) + '\t' + type_nb_name + '\t' + final_type_name + '\n')

                            if prob > next_type_prob:
                                next_type_prob = prob
                                next_type = type_nb

                        if next_type == None:
                            print()
                        # entity
                        next_entity, next_entity_prob = None, 0
                        next_entity_back, next_entity_prob_back = None, 0
                        last_entity_idx = session_entity_seq[-1]
                        need_back = True
                        any_valid_nb = False

                        for entity_nb in entity_nb_dict[last_entity_idx]:
                            next_goal_type_name = idx2type[next_type]
                            cur_goal_entity_name = idx2entity[entity_nb]
                            if next_goal_type_name not in entity_same_as_type \
                                    and cur_goal_entity_name in entity_same_as_type:
                                continue

                            entity_nb_name = idx2entity[entity_nb]
                            if entity_nb_name != idx2entity[last_entity_idx] \
                                and entity_nb_name != "再见" \
                                and (entity_nb_name.replace("新闻", "") in kg_entitys or entity_nb_name in idx2type):
                            # if nb_name.replace("新闻", "") in kg_entitys \
                            #         or (nb_name in idx2type and nb_name != idx2entity[last_entity_idx]
                            #             and nb_name != "再见"):
                                past_entity_seq = session_entity_seq + [entity_nb]
                                prob = goal_planning.goal_entity_infer(past_entity_seq, last_entity_idx, final_entity_idx)

                                #debug
                                past_entity_seq_name = [idx2entity[idx] for idx in past_entity_seq]
                                cur_entity_name = idx2entity[last_entity_idx]
                                final_entity_name = idx2entity[final_entity_idx]
                                goal_entity_debug.write(str(cur_session_id) + '-' + str(last_round_id) + ':' + str(prob) + '\t' +
                                                        str(past_entity_seq_name) + '\t' + cur_entity_name + '\t' + final_entity_name + '\n')

                                if prob > next_entity_prob_back:
                                    any_valid_nb = True
                                    next_entity_prob_back = prob
                                    next_entity_back = entity_nb

                                if prob > next_entity_prob:
                                    # if "明星" in next_goal_type_name and cur_goal_entity_name not in stars:
                                    if "明星" in next_goal_type_name \
                                            and cur_goal_entity_name not in user_profile["喜欢 的 明星"]\
                                            and cur_goal_entity_name not in star:
                                        # print("明星", next_goal_type_name, cur_goal_entity_name)
                                        continue
                                    if "音乐" in next_goal_type_name \
                                            and cur_goal_entity_name not in song:
                                        # print("音乐", next_goal_type_name, cur_goal_entity_name)
                                        continue
                                    if "音乐" in next_goal_type_name \
                                        and last_round_id == round_id \
                                        and cur_goal_entity_name in ' '.join(utt_lst):
                                        continue
                                    if "新闻" in next_goal_type_name \
                                            and "新闻" not in cur_goal_entity_name\
                                            and "新闻" not in news:
                                        # print("新闻", next_goal_type_name, cur_goal_entity_name)
                                        continue
                                    if "电影" in next_goal_type_name \
                                            and next_goal_type_name not in mv:
                                        # print("电影", next_goal_type_name, cur_goal_entity_name)
                                        continue
                                    # if "美食" in next_goal_type_name and cur_goal_entity_name not in foods:
                                    if "美食" in next_goal_type_name \
                                            and cur_goal_entity_name not in user_profile["同意 的 美食"]\
                                            and cur_goal_entity_name not in food:
                                        # print("美食", next_goal_type_name, cur_goal_entity_name)
                                        continue
                                    # if "兴趣点" in next_goal_type_name and cur_goal_entity_name not in pois:
                                    if "兴趣点" in next_goal_type_name \
                                            and cur_goal_entity_name not in user_profile["喜欢 的 poi"]\
                                            and cur_goal_entity_name not in poi:
                                        # print("兴趣点", next_goal_type_name, cur_goal_entity_name)
                                        continue

                                    need_back = False
                                    next_entity_prob = prob
                                    next_entity = entity_nb

                        if any_valid_nb == False:
                            next_entity = last_entity_idx
                        elif need_back == True:
                            next_entity = next_entity_back

                    session_type_seq.append(next_type)
                    session_entity_seq.append(next_entity)
                    last_round_id += 1

            # next_types.append(idx2type[next_type])
            # next_entitys.append(idx2entity[next_entity])
            type_seq_name = [idx2type[idx] for idx in session_type_seq]
            entity_seq_name = [idx2entity[idx] for idx in session_entity_seq]
            next_types.append(type_seq_name)
            next_entitys.append(entity_seq_name)
            # session_type_seq.append(next_type)
            # session_entity_seq.append(next_entity)
            last_session_id = cur_session_id
            last_round_id = round_id

        next_goal = zip(next_types, next_entitys, goal_finishes, session_id, round_ids)
        with open('../../output/next_goal.txt', 'w', encoding='utf-8') as f:
            for goal in next_goal:
                f.write(str(goal) + '\n')


if __name__ == '__main__':
    config = Config()
    infer(config)
