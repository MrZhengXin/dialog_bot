import json
import re


def word_replace(word):
    word = word.replace(' ', '').replace('\n', '')
    word = word.replace("问User", "问用户").replace("poi推荐", "兴趣点推荐").replace("的新闻", "新闻")
    word = word.replace("说A好的幸福呢", "说好的幸福呢")
    word = re.sub(r"\[\d*\]", "", word)
    word = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', word)
    return word


def extract_entity(input_path, output_path):
    # 对话类型
    bad_flag = ["参考知识"]
    flag = ["再见", "问天气", "问时间", "天气信息推送", '问User爱好', '问User年龄', '问User性别', '问User姓名']  # 无关键词
    flag1 = ["关于明星的聊天", "音乐推荐", "播放音乐", "美食推荐",
             "电影推荐", "音乐点播", "问日期", "新闻推荐", "新闻点播", "提问", "兴趣点推荐"]  # 一个关键词
    flag2 = ["问答"]
    flag3 = ["寒暄"]
    # all_flag = bad_flag + flag2 + flag + flag1

    output = open(output_path, 'w', encoding='utf-8')

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f.readlines():
            data = json.loads(line)
            goals = data['goal'].split('-->')

            entitys = []
            for goal in goals:
                type = goal.split(']', 1)[-1].split('(', 1)[0].replace(' ', '')

                if "『" and "』" not in goal or type == "问日期":
                    entity = type
                elif type in flag1:
                    entity = goal.split("『", 1)[-1].split("』", 1)[0].replace(' ', '')  # 由『』给出的第一个关键词
                    if "新闻" in goal:
                        entity += "新闻"
                elif type in flag2:
                    entity1 = goal.split("『", 1)[-1].split("』", 1)[0].replace(' ', '')
                    entity2 = goal.split("『", -1)[-1].split("』", -1)[0].replace(' ', '')

                    if entity1 not in bad_flag:
                        entity = entity1
                    else:
                        entity = entity2
                else:
                    entity = type

                entitys.append(word_replace(entity))

            output.write(str(entitys) + '\n')

    output.close()


if __name__ == '__main__':
    input_prefix = "../../data/origin/"
    output_prefix = "../../data/train/"
    extract_entity(input_prefix + "train.txt", output_prefix + "train_entity.txt")
    extract_entity(input_prefix + "dev.txt", output_prefix + "val_entity.txt")
