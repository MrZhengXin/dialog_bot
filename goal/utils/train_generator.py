#!/usr/bin/python
# -*- coding: UTF-8 -*-
import random

random.seed(42)


class Dataset(object):
    def __init__(self, data_tag):
        self.data_path = "../data/process/"
        self.utterance = self.file_loader(self.data_path + data_tag + "_utterance.txt")
        self.goal_type = self.file_loader(self.data_path + data_tag + "_type.txt")
        self.goal_entity = self.file_loader(self.data_path + data_tag + "_entity.txt")
        self.bot = self.file_loader(self.data_path + data_tag + "_bot.txt")
        self.label = self.file_loader(self.data_path + data_tag + "_label.txt")

        self.other_path = "../data/others/"
        self.goal_type_graph_dict = self.file_loader(self.other_path + "goal_type_neighbour.txt")
        self.goal_entity_graph_dict = self.file_loader(self.other_path + "goal_entity_neighbour.txt")

    def file_loader(self, file_path):
        with open(file_path, "r", encoding='utf-8') as f:
            data = eval(f.read())
        return data

    def binary_task_data(self):
        binary_utterance, binary_goal_type, bianry_label = list(), list(), list()

        for idx in range(len(self.utterance)):
            line_len = len(self.utterance[idx])
            for jdx in range(1, line_len):
                # 前一个对话的utter, type预测goal是否完成（一轮对话是否结束）
                if self.bot[idx][jdx] == 1:  # 是bot
                    if self.utterance[idx][max(0, jdx-2)]:
                    # if self.utterance[idx][0]:
                        utt_flat = [utt for utts in self.utterance[idx][max(0, jdx-2):jdx] for utt in utts]
                        # utt_flat = [utt for utts in self.utterance[idx][:jdx] for utt in utts]
                        binary_utterance.append(utt_flat)
                        binary_goal_type.append(self.goal_type[idx][jdx - 1])
                        bianry_label.append(self.label[idx][jdx])
        return binary_utterance, binary_goal_type, bianry_label

    def remove_repeat(self, goal_seq, kg_seq):
        """去除重复的(goal_seq, kg_seq)pair"""
        assert len(goal_seq) == len(kg_seq)
        new_goal_seq, new_kg_seq = list(), list()
        for idx, (a, b) in enumerate(zip(goal_seq, kg_seq)):
            if idx > 0 and a == goal_seq[idx - 1] and b == kg_seq[idx - 1]:
                continue
            new_goal_seq.append(a)
            new_kg_seq.append(b)

        return new_goal_seq, new_kg_seq

    def next_goal_data(self, undersample=False):
        binary_utterance = list()
        binary_goal_type, binary_final_goal_type, binary_goal_type_label, binary_goal_type_idx = list(), list(), list(), list()
        binary_goal_entity, binary_final_goal_entity, binary_goal_entity_label, binary_goal_entity_idx = list(), list(), list(), list()

        for idx in range(len(self.goal_type)):
            line_len = len(self.goal_type[idx])
            for jdx in range(1, line_len):
                if self.bot[idx][jdx] == 1 and self.utterance[idx][jdx - 1]:
                    binary_utterance.append(self.utterance[idx][jdx - 1])
                    # 历史对话的所有type entity
                    pre_type_seq = self.goal_type[idx][:jdx]
                    pre_entity_seq = self.goal_entity[idx][:jdx]
                    if len(pre_type_seq) == 0 or len(pre_entity_seq) == 0:
                        continue
                    pre_type_seq, pre_entity_seq = self.remove_repeat(pre_type_seq, pre_entity_seq)
                    # goal
                    for nb in self.goal_type_graph_dict[pre_type_seq[-1]]:
                        # 历史对话的所有type + 前一个对话的type的neighbour
                        binary_goal_type.append(pre_type_seq + [nb])
                        # binary_goal_type_idx.append(idx)
                        # label：是不是真的neighbour
                        if nb == self.goal_type[idx][jdx]:
                            binary_goal_type_label.append(1)
                        else:
                            binary_goal_type_label.append(0)

                        # 最后一个goal type
                        for type in self.goal_type[idx][::-1]:
                            if type != self.goal_type[idx][-1]:
                                binary_final_goal_type.append(type)
                                break
                        # binary_final_goal_type.append(self.goal_type[idx][-2])
                    # entity
                    cnt = 0
                    for nb in self.goal_entity_graph_dict[pre_entity_seq[-1]]:
                        # 前一次对话的entity的邻居就是当前对话的entity
                        if nb == self.goal_entity[idx][jdx]:
                            binary_goal_entity.append(pre_entity_seq + [nb])
                            binary_goal_entity_label.append(1)
                            cnt += 1
                        else:
                            # 不是所有相邻entity都用到，至少10个，但是随机处理的方式过于简单
                            if cnt > 10 and random.random() > 0.2:
                                continue
                            binary_goal_entity.append(pre_entity_seq + [nb])
                            binary_goal_entity_label.append(0)
                            cnt += 1

                        # binary_goal_entity_idx.append(idx)
                        for entity in self.goal_entity[idx][::-1]:
                            if entity != self.goal_entity[idx][-1]:
                                binary_final_goal_entity.append(entity)
                                break

        return binary_goal_type, binary_goal_type_label, binary_goal_entity, binary_goal_entity_label, binary_final_goal_type, binary_final_goal_entity, binary_utterance


def file_saver(file_path, obj):
    with open(file_path, "w", encoding='utf-8') as f:
        f.write(str(obj))


def get_data(data_tag, undersample=False):
    data = Dataset(data_tag)
    binary_utterance, binary_goal_type, binary_label = data.binary_task_data()
    next_goal_type, next_goal_type_label, next_goal_entity, next_goal_entity_label, final_goal_type, final_goal_entity, next_goal_utterance = data.next_goal_data(
        undersample=undersample)

    print("Binary Jump Classification...")
    print("Sample Numebr: %d, Jump Number: %d, Jump Rate: %.2f" % (
        len(binary_utterance), sum(binary_label), float(sum(binary_label)) / len(binary_utterance)))
    print("Next Goal Type Prediction...")
    print("Sample Numebr: %d, True Number: %d, True Rate: %.2f" % (
        len(next_goal_type), sum(next_goal_type_label), float(sum(next_goal_type_label)) / len(next_goal_type)))
    print("Next Goal Entity Prediction...")
    print("Sample Numebr: %d, True Number: %d, True Rate: %.2f\n" % (
        len(next_goal_entity), sum(next_goal_entity_label), float(sum(next_goal_entity_label)) / len(next_goal_entity)))

    save_path = "../data/train/"
    file_saver(save_path + data_tag + "_binary_utterance.txt", binary_utterance)
    file_saver(save_path + data_tag + "_binary_goal_type.txt", binary_goal_type)
    file_saver(save_path + data_tag + "_binary_label.txt", binary_label)
    file_saver(save_path + data_tag + "_next_goal_type.txt", next_goal_type)
    # file_saver(save_path + data_tag + "_next_goal_type_idx.txt", next_goal_type_idx)
    file_saver(save_path + data_tag + "_next_goal_type_label.txt", next_goal_type_label)
    file_saver(save_path + data_tag + "_next_goal_entity.txt", next_goal_entity)
    # file_saver(save_path + data_tag + "_next_goal_entity_idx.txt", next_goal_entity_idx)
    file_saver(save_path + data_tag + "_next_goal_entity_label.txt", next_goal_entity_label)
    file_saver(save_path + data_tag + "_final_goal_type.txt", final_goal_type)
    file_saver(save_path + data_tag + "_final_goal_entity.txt", final_goal_entity)
    file_saver(save_path + data_tag + "_next_goal_utterance.txt", next_goal_utterance)


if __name__ == "__main__":
    get_data(data_tag="train", undersample=True)
    get_data(data_tag="val")
