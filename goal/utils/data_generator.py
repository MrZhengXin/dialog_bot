#!/usr/bin/python
# -*- coding: UTF-8 -*-
import re
from collections import defaultdict

import numpy as np
import random
random.seed(42)


def file_loader(file_path):
    with open(file_path, "r", encoding='utf-8') as f:
        data = eval(f.read())
    return data


def file_saver(file_path, obj):
    with open(file_path, "w", encoding='utf-8') as f:
        f.write(str(obj))


def file_reader(file_path):
    utterance, label, goal_type, goal_entity, bot_flag = list(), list(), list(), list(), list()

    with open(file_path, "r", encoding='utf-8') as f:
        utt, lab, gtp, get, bfl = list(), list(), list(), list(), list()

        for line in f.readlines():
            if line == "\n":
                utterance.append(utt)
                label.append(lab)
                goal_type.append(gtp)
                goal_entity.append(get)
                bot_flag.append(bfl)

                utt, lab, gtp, get, bfl = list(), list(), list(), list(), list()
            else:
                line = line.split("\t")
                if line[0] == "":
                    if line[2] == "再见":
                        utt.append("再见")
                    if line[2] == "音乐推荐":
                        utt.append("给你推荐一首歌吧")
                    else:
                        continue
                else:
                    utt.append(line[0])

                if line[1] == "":
                    lab.append(int(line[2]))
                    gtp.append(line[3])
                    if line[4] == "":
                        get.append(line[3])
                    else:
                        get.append(line[4])
                else:
                    lab.append(int(line[1]))
                    gtp.append(line[2])
                    if line[3] == "":
                        get.append(line[2])
                    else:
                        get.append(line[3])
                    bfl.append(line[-1].replace("\n", ""))

    return utterance, goal_type, goal_entity, bot_flag, label


def get_word_dict(utterances):
    stop_words = list()
    with open("../data/others/stop_words.txt", "r", encoding='utf-8') as f:
        for line in f.readlines():
            stop_words.append(line.replace("\n", ""))

    word_set = set()
    for utt in utterances:
        for u in utt:
            # 去除标点，数字和[1]
            u = re.sub(r"\[\d*\]", "", u)
            u = re.sub(r"[~`!#$%^&*()_+-=|';\":/.,?><~·！@#￥%……&*（）——+-=“：’；、。，？》《{}]+", "", u)
            for word in u.strip().split():
                if word is not "":  # 原先没有过滤停用词
                    word_set.add(word)

    word_dict = dict()
    word_dict["PAD"] = 0
    word_dict["UNK"] = 1
    for i, word in enumerate(word_set):
        word_dict[word] = i + 2

    print("word dict size: %d" % (len(word_dict)))
    file_saver("../data/others/word_dict.txt", word_dict)
    return word_dict


def remove_punctuation(line):
    line = re.sub(r"\[\d*\]", "", line)
    return re.sub(r'[^\u4e00-\u9fa5^a-z^A-Z^0-9]', '', line)


def word_replace(word):
    word = word.replace(' ', '').replace('\n', '')
    word = word.replace("问User", "问用户").replace("poi推荐", "兴趣点推荐").replace("的新闻", "新闻")
    word = word.replace("说A好的幸福呢", "说好的幸福呢")
    word = remove_punctuation(word)
    return word


def text_generator(word_dict, documents):
    texts_idx = list()
    UNK = word_dict["UNK"]
    for doc in documents:
        doc_idx = list()
        for line in doc:
            line = re.sub("\[\d*\]", "", line)
            line = re.sub(
                r'[~`!#$%^&*()_+-=|\';":/.,?><~·！@#￥%……&*（）——+-=“：’；、。，？》《{}]+', "", line)
            line_idx = [word_dict.get(word, UNK) for word in line.strip().split() if word != ""]
            doc_idx.append(line_idx)
        texts_idx.append(doc_idx)
    return texts_idx


def data_idx(utt, type, entity, bot, label, word_dict, type_dict, entity_dict, bot_dict, save_tag):
    utt_idx = text_generator(word_dict, utt)
    type_idx = list()
    entity_idx = list()
    bot_idx = list()
    for idx in range(len(type)):
        type_idx.append([type_dict[word_replace(word)]
                         for word in type[idx]])
        entity_idx.append([entity_dict[word_replace(word)] for word in entity[idx]])
        bot_idx.append([bot_dict[b] for b in bot[idx]])

    file_saver("../data/process/" + save_tag + "_utterance.txt", utt_idx)
    file_saver("../data/process/" + save_tag + "_type.txt", type_idx)
    file_saver("../data/process/" + save_tag + "_entity.txt", entity_idx)
    file_saver("../data/process/" + save_tag + "_bot.txt", bot_idx)
    file_saver("../data/process/" + save_tag + "_label.txt", label)

    return {
        'utt_idx': utt_idx,
        'type_idx': type_idx,
        'entity_idx': entity_idx,
        'bot_idx': bot_idx
    }


def get_graph(train_data, val_data, graph_size, save_tag, item_dict=None, flag=False):
    # 对角线置1
    graph = np.eye(graph_size, graph_size)
    # 一个session中相邻type or entity置1
    for idx in range(len(train_data)):
        for jdx in range(len(train_data[idx]) - 1):
            graph[train_data[idx][jdx]][train_data[idx][jdx + 1]] = 1
    for idx in range(len(val_data)):
        for jdx in range(len(val_data[idx]) - 1):
            graph[val_data[idx][jdx]][val_data[idx][jdx + 1]] = 1

    if save_tag == "entity" and item_dict:
        graph[item_dict["问天气"]][item_dict["时光机"]] = 1
        graph[item_dict["问天气"]][item_dict["流泪手心"]] = 1

    if flag:
        # 关系：明星和对应的新闻
        all_star = file_loader("../data/others/all_star.txt")
        for star in all_star:
            graph[item_dict[star]][item_dict[star + "新闻"]] = 1
        # 关系：明星和参演的影视剧
        with open("../data/others/final_star2movie.txt", "r", encoding='utf-8') as f:
            for movie in f.readlines():
                star, movie_list = movie.split("\001")
                star = remove_punctuation(star)
                if star in all_star:
                    movie_list = [remove_punctuation(mv) for mv in movie_list.split("\t")]
                    for mv in movie_list:
                        graph[item_dict[star]][item_dict[mv]] = 1
                        graph[item_dict[mv]][item_dict[star]] = 1
        # 关系：歌手和唱的歌
        with open("../data/others/singer2song_with_comment.txt", "r", encoding='utf-8') as f:
            for music in f.readlines():
                star, music_list = music.split("\001")
                star = remove_punctuation(star)
                if star in all_star:
                    music_list = [remove_punctuation(mc) for mc in music_list.split("\t")]
                    for mc in music_list:
                        graph[item_dict[star]][item_dict[mc]] = 1
                        graph[item_dict[mc]][item_dict[star]] = 1
                    for i in music_list:
                        for j in music_list:
                            if i != j:
                                graph[item_dict[i]][item_dict[j]] = 1

        # 关系：城市和POI，城市和菜，POI和菜，菜和POI
        with open("../data/others/food_kg_human_filter.json", "r", encoding='utf-8') as f:
            for line in f.readlines():
                line = eval(line)
                city = remove_punctuation(line["city"])
                poi = remove_punctuation(line["shopName"])
                food = remove_punctuation(line["name"])
                graph[item_dict[city]][item_dict[poi]] = 1
                graph[item_dict[city]][item_dict[food]] = 1
                graph[item_dict[poi]][item_dict[food]] = 1
                graph[item_dict[food]][item_dict[poi]] = 1

    # np.save("../data/others/graph_" + save_tag + "_graph", graph)
    return graph


def goal_type_entity_dict():
    # goal_type and entity dict
    data_prefix = "../data/others/"
    all_goal_type = file_loader(data_prefix + "all_goal_type.txt")
    all_goal_entity = file_loader(data_prefix + "all_goal_entity.txt")
    all_goal_entity = set.union(all_goal_type, all_goal_entity)
    print("goal type size:", len(all_goal_type))
    print("goal entity size:", len(all_goal_entity))

    all_goal_type_dict = dict()
    for i, item in enumerate(all_goal_type):
        all_goal_type_dict[item] = i
    all_goal_entity_dict = dict()
    cnt = 0
    for item in all_goal_entity:
        if all_goal_entity_dict.get(item) == None:
            all_goal_entity_dict[item] = cnt
            cnt += 1
    file_saver("../data/others/goal_type_dict.txt", all_goal_type_dict)
    file_saver("../data/others/goal_entity_dict.txt", all_goal_entity_dict)

    return all_goal_type_dict, all_goal_entity_dict


def save_goal_type_entity_neighbour(goal_type_graph, goal_entity_graph):
    goal_type_neighbour = defaultdict(list)
    goal_entity_neighbour = defaultdict(list)
    for idx, line in enumerate(goal_type_graph):
        for jdx, num in enumerate(line):
            if num == 1:
                goal_type_neighbour[idx].append(jdx)
    for idx, line in enumerate(goal_entity_graph):
        for jdx, num in enumerate(line):
            if num == 1:
                goal_entity_neighbour[idx].append(jdx)

    file_saver("../data/others/goal_type_neighbour.txt",
               dict(goal_type_neighbour))
    file_saver("../data/others/goal_entity_neighbour.txt",
               dict(goal_entity_neighbour))
    return goal_type_neighbour, goal_entity_neighbour


def save_test_data(word_dict, goal_type_dict, goal_entity_dict, type_nb_dict, entity_nb_dict):
    binary_utterance, binary_label, binary_goal_type = list(), list(), list()
    next_goal_type, next_goal_entity, next_final_goal_type, next_final_goal_entity = list(), list(), list(), list()
    round_ids, max_ids, session_ids = list(), list(), list()
    UNK = word_dict["UNK"]
    # debug
    entity_debug = open("../data/others/test_entity_debug.txt", 'w', encoding='utf-8')
    idx2entity = list(goal_entity_dict.keys())

    total_cnt = 0
    with open("../data/process/test.txt", "r", encoding='utf-8') as f:
        for idx, line in enumerate(f.readlines()):
            if line == "\n":
                continue
            line = line.split("\t")

            # if utterance == "":
            #     continue
            session_cnt = int(line[0])
            session_ids.append(session_cnt)
            history = ' '.join(line[1].split("\001"))
            round_id = re.findall(r"\[(\d*)\]", history)
            if len(round_id) > 0:
                round_ids.append(int(round_id[-1]))
            else:
                round_ids.append(1)
            max_ids.append(int(line[-1].replace('\n', '')))

            utterance = line[1].split("\001")[-1]
            utterance = re.sub("\[\d*\]", "", utterance)
            utterance = re.sub(
                r'[~`!#$%^&*()_+-=|\';":/.,?><~·！@#￥%……&*（）——+-=“：’；、。，？》《{}]+', "", utterance)
            utterance = [word_dict.get(word, UNK) for word in utterance.strip().split() if word != ""]
            # if not utterance:
            #     continue
            # 评估当前goal是否完成
            binary_utterance.append(utterance)
            binary_label.append(int(line[2]))
            binary_goal_type.append(goal_type_dict[word_replace(line[3])])
            # 预测下一个goal的type
            type_seq_candidate = list()
            first_type_idx = goal_type_dict[word_replace(line[3])]
            for nb in type_nb_dict[first_type_idx]:
                if nb == first_type_idx and len(type_nb_dict[first_type_idx]) > 1:
                    continue
                type_seq_candidate.append([first_type_idx, nb])
            next_goal_type.append(type_seq_candidate)
            next_final_goal_type.append(goal_type_dict[word_replace(line[5])])
            # next_goal_type_idx.append(idx)
            # topic
            kgs = eval(line[7])
            kg_entitys = []
            kg_entitys_debug = []
            for kg in kgs:
                for item in kg:
                    item = word_replace(item)
                    if item in goal_entity_dict.keys():
                        kg_entitys.append(goal_entity_dict[item])
                        kg_entitys_debug.append(item)
            kg_entitys = list(set(kg_entitys))
            kg_entitys_debug = list(set(kg_entitys_debug))

            entity_seq_candidate = list()
            entity_seq_candidate_debug = list()
            first_entity_idx = goal_entity_dict[word_replace(line[4])]
            nb_debug = []
            for nb in entity_nb_dict[first_entity_idx]:
                nb_name = idx2entity[nb]
                nb_debug.append(nb_name)
                # if nb not in kg_entitys or (nb == first_entity_idx and len(entity_nb_dict[first_entity_idx]) > 1):
                if nb_name.replace("新闻", "") in kg_entitys_debug \
                        or (nb_name in list(goal_type_dict.keys()) and nb_name != word_replace(line[4])
                            and nb_name != "再见"):
                    entity_seq_candidate.append([first_entity_idx, nb])
                    entity_seq_candidate_debug.append([idx2entity[first_entity_idx], idx2entity[nb]])
            if len(entity_seq_candidate) == 0:
                print(total_cnt + 1)
                entity_seq_candidate = [first_entity_idx, first_entity_idx]
                entity_seq_candidate_debug = [idx2entity[first_entity_idx], idx2entity[first_entity_idx]]

            entity_debug.write('nb:' + str(nb_debug))
            entity_debug.write('kg_entitys:' + str(kg_entitys_debug))
            entity_debug.write('entity_seq_candidate:' + str(entity_seq_candidate_debug))
            entity_debug.write('\n')

            next_goal_entity.append(entity_seq_candidate)
            next_final_goal_entity.append(goal_entity_dict[word_replace(line[6])])
            # next_goal_entity_idx.append(idx)

            total_cnt += 1

    entity_debug.close()
    print('test data size:', total_cnt)
    save_path = "../data/train/"
    data_tag = "test"
    file_saver(save_path + data_tag + "_binary_utterance.txt", binary_utterance)
    file_saver(save_path + data_tag + "_binary_goal_type.txt", binary_goal_type)
    file_saver(save_path + data_tag + "_binary_label.txt", binary_label)
    file_saver(save_path + data_tag + "_next_goal_type.txt", next_goal_type)
    # file_saver(save_path + data_tag + "_next_goal_type_idx.txt", next_goal_type_idx)
    file_saver(save_path + data_tag + "_next_goal_entity.txt", next_goal_entity)
    # file_saver(save_path + data_tag + "_next_goal_entity_idx.txt", next_goal_entity_idx)
    file_saver(save_path + data_tag + "_final_goal_type.txt", next_final_goal_type)
    file_saver(save_path + data_tag + "_final_goal_entity.txt", next_final_goal_entity)
    file_saver(save_path + data_tag + "_round_id.txt", round_ids)
    file_saver(save_path + data_tag + "_max_id.txt", max_ids)
    file_saver(save_path + data_tag + "_session_id.txt", session_ids)


def main():
    # read train and val origin data
    train_utt, train_type, train_entity, train_bot, train_label = file_reader(train_data_path)
    val_utt, val_type, val_entity, val_bot, val_label = file_reader(val_data_path)
    # word_dict
    word_dict = get_word_dict(train_utt)
    # goal type and entity dict
    all_goal_type_dict, all_goal_entity_dict = goal_type_entity_dict()
    # bot dict
    bot_dict = {"Bot": 1, "User": 0}

    # train dev data
    train_idx = data_idx(train_utt, train_type, train_entity, train_bot, train_label, word_dict, all_goal_type_dict,
                         all_goal_entity_dict, bot_dict, "train")
    val_idx = data_idx(val_utt, val_type, val_entity, val_bot, val_label, word_dict, all_goal_type_dict,
                       all_goal_entity_dict, bot_dict, "val")

    # goal type and entity graph
    goal_type_graph = get_graph(
        train_idx['type_idx'], val_idx['type_idx'], len(all_goal_type_dict), "type")
    goal_entity_graph = get_graph(
        train_idx['entity_idx'], val_idx['entity_idx'], len(all_goal_entity_dict), "entity", all_goal_entity_dict,
        flag=True)
    # goal type and entity neighbour
    type_nb_dict, entity_nb_dict = save_goal_type_entity_neighbour(goal_type_graph, goal_entity_graph)

    # save_test_data(word_dict, all_goal_type_dict, all_goal_entity_dict, type_nb_dict, entity_nb_dict)


if __name__ == "__main__":
    # data path
    origin_data_path = "../data/process/"
    train_data_path = origin_data_path + "train.txt"
    val_data_path = origin_data_path + "dev.txt"
    test_data_path = origin_data_path + "test.txt"
    main()
