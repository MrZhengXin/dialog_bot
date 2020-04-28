import json


def is_start_with(str):
    start_str = ['[1]', '[2]', '[3]', '[4]', '[5]', '[6]', '[7]', '[8]']
    for s in start_str:
        if str.startswith(s):
            return 1
    return 0


def add_label(input_filename, output_filename):
    output_file = open(output_filename, 'w', encoding='utf-8')
    with open(input_filename, 'r', encoding='utf-8') as f:
        for line in f.readlines():
            data = json.loads(line.strip())
            conversation = data['conversation']
            label = []
            for c in conversation:
                label.append(is_start_with(c.strip()))
            data['label'] = label
            output_file.write(json.dumps(data, ensure_ascii=False) + '\n')
    output_file.close()


def process_session_data(input_filename, output_filename):
    # 对话类型
    bad_flag = ["参考知识"]
    flag = ["再见", "问天气", "问时间", "天气信息推送"]  # 无关键词
    flag1 = ["关于明星的聊天", "音乐推荐", "播放音乐", "美食推荐",
             "电影推荐", "音乐点播", "问日期", "新闻推荐", "新闻点播"]  # 一个关键词
    flag2 = ["问答"]
    flag3 = ["寒暄"]
    flag4 = ['问User爱好', '问User年龄', '问User性别', '问User姓名']
    flag5 = ['提问']
    flag6 = ['兴趣点推荐']
    all_flag = bad_flag + flag2 + flag + flag1

    # user_profile key  没有考虑存在空格的情况
    p_r_key = ["拒绝"]
    p_p_key = ["喜欢的电影", "喜欢的明星", "喜欢的poi", "喜欢的音乐", "喜欢的新闻", "喜欢的兴趣点"]
    p_a_key = ["同意的新闻", "同意的音乐", "同意的美食", "同意的poi", "同意的电影", "喜欢的兴趣点"]
    p_key = ["接受的电影", "接受的音乐", "没有接受的电影", "没有接受的音乐"]
    list_key = ["同意的新闻", "没有接受的音乐", "接受的电影",
                "喜欢的明星", "接受的音乐", "没有接受的电影", "喜欢的新闻"]
    keyword_list = p_p_key + p_a_key + p_r_key + p_key

    output_file = open(output_filename, 'w', encoding='utf-8')
    # user_profile_key_result = set()  # 记录所有user_profile的Key

    for line in open(input_filename, 'r', encoding='utf-8'):
        # flag_flag = 0
        entity_level_goal = ""

        data = json.loads(line.strip())
        # situation = data['situation']
        conversation = data['conversation']
        goals = data['goal'].split('-->')
        label = data["label"]
        kg = data["knowledge"]
        user_profile = data["user_profile"]

        if len(goals) != sum(label):  # 去除无效data
            continue

        used_kg_entity = set()  # 记录knowledge中的所有subject
        for (s, r, o) in kg:
            if r != "适合吃" and s != '聊天':    # 困惑？？？
                used_kg_entity.add(s)
        used_kg_entity = list(used_kg_entity)

        # user_profile_key_result = list()
        # for key in user_profile:
        #     user_profile_key_result.append(key)

        # 存在问题：keyword_list 没有考虑空格
        profile_entity_list = set()  # 记录user_profile所有的value
        for key in user_profile:
            if key.replace(' ', '') not in keyword_list:
                continue
            tmp_entity = user_profile[key]
            if isinstance(tmp_entity, list):
                for k in tmp_entity:
                    profile_entity_list.add(k.strip())
            else:
                profile_entity_list.add(tmp_entity.strip())
        profile_entity_list = list(profile_entity_list)

        count = 1  # 第几轮对话
        current_topic = ""  # 当前这一轮对话的话题
        type = ""  # 对话类型
        # 问题：没有去除空格
        first_goal = goals[0].strip().split(']', maxsplit=1)[1].split('(', maxsplit=1)[0]

        for i in range(len(label)):
            if first_goal.replace(' ', '') == '寒暄':  # 只有寒暄是机器先开始session
                if i % 2 == 0:
                    dialog_flag = 'Bot'
                else:
                    dialog_flag = 'User'
            else:
                if i % 2 != 0:
                    dialog_flag = 'Bot'
                else:
                    dialog_flag = 'User'

            if label[i] == 1:  # 一轮对话的开头
                if count == 1:  # 第一轮对话开头肯定还没有结束
                    label[i] = 0

                current_goal = goals[count - 1].split('[{0}]'.format(count))[-1]  # 当前目标
                type = current_goal.split('(', 1)[0]  # 对话具体要求

                if "『" and "』" not in current_goal:
                    # 对话内容+是否为一轮对话的开头+对话类型+对话话题+背景知识+用户画像+当前哪一方说话 （遗漏了对话场景）
                    output_file.write(
                        conversation[i] + '\t' + str(label[i]) + '\t' + type + '\t' + type + '\t' + str(
                            kg) + '\t' + str(user_profile) + '\t' + dialog_flag + '\n')
                    current_topic = type  # 当前这一轮对话的话题

                else:
                    if type in flag1:  # 一个关键词
                        topic = current_goal.split("『", 1)[-1].split("』", 1)[0]  # 由『』给出的第一个关键词
                        if type.replace(' ', '') == "问日期":
                            output_file.write(
                                conversation[i] + '\t' + str(label[i]) + '\t' + type + '\t' + type + '\t' + str(
                                    kg) + '\t' + str(user_profile) + '\t' + dialog_flag + '\n')
                            current_topic = type

                        elif "新闻" in type:
                            output_file.write(conversation[i] + '\t' + str(
                                label[i]) + '\t' + type + '\t' + topic + " 新闻" + '\t' + str(
                                kg) + '\t' + str(user_profile) + '\t' + dialog_flag + '\n')
                            current_topic = topic + " 新闻"

                        else:
                            output_file.write(
                                conversation[i] + '\t' + str(label[i]) + '\t' + type + '\t' + topic + '\t' + str(
                                    kg) + '\t' + str(user_profile) + '\t' + dialog_flag + '\n')
                            current_topic = topic

                    elif type in flag2:  # 问答
                        topic1 = current_goal.split("『", 1)[-1].split("』", 1)[0]
                        topic2 = current_goal.split("『", -1)[-1].split("』", -1)[0]

                        if topic1.replace(' ', '') not in bad_flag:  # 不用参考知识
                            output_file.write(
                                conversation[i] + '\t' + str(label[i]) + '\t' + type + '\t' + topic1 + '\t' + str(
                                    kg) + '\t' + str(user_profile) + '\t' + dialog_flag + '\n')
                        else:  # 需要参考知识
                            output_file.write(
                                conversation[i] + '\t' + str(label[i]) + '\t' + type + '\t' + topic2 + '\t' + str(
                                    kg) + '\t' + str(user_profile) + '\t' + dialog_flag + '\n')
                        current_topic = topic2

                    else:  # 其他（闲聊？是否还要再分？）
                        output_file.write(
                            conversation[i] + '\t' + str(label[i]) + '\t' + type + '\t' + type + '\t' + str(
                                kg) + '\t' + str(user_profile) + '\t' + dialog_flag + '\n')
                count += 1

            else:  # 非一轮对话开头
                output_file.write(conversation[i] + '\t' + str(label[i]) + '\t' + type + '\t' +
                                  current_topic + '\t' + str(kg) + '\t' + str(user_profile) + '\t' + dialog_flag + '\n')
        output_file.write('\n')
    output_file.close()


def process_test_data(input_filename, output_filename):
    # 对话类型
    bad_flag = ["参考知识"]
    flag = ["再见", "问天气", "问时间", "天气信息推送"]
    flag1 = ["关于明星的聊天", "音乐推荐", "播放音乐", "美食推荐", "poi推荐",
             "电影推荐", "音乐点播", "问日期", "新闻推荐", "新闻点播", "", "", ""]
    flag2 = ["问答", "新闻 点播", "音乐 点播"]
    flag3 = ["问 User 爱好", "天气 信息 推送"]
    flag4 = ["新闻 推荐"]
    all_flag = bad_flag + flag2 + flag + flag1

    # user_profile key
    p_r_key = ["拒绝"]
    p_p_key = ["喜欢的电影", "喜欢的明星", "喜欢的poi", "喜欢的音乐", "喜欢的新闻"]
    p_a_key = ["同意的新闻", "同意的音乐", "同意的美食", "同意的poi", "同意的电影"]
    p_key = ["接受的电影", "接受的音乐", "没有接受的电影", "没有接受的音乐"]
    list_key = ["同意的新闻", "没有接受的音乐", "接受的电影",
                "喜欢的明星", "接受的音乐", "没有接受的电影", "喜欢的新闻"]
    keyword_list = p_p_key + p_a_key + p_r_key

    output_file = open(output_filename, 'w', encoding='utf-8')
    last_utterance = ''
    last_kg = None
    begin_of_file = True

    for line in open(input_filename, 'r', encoding='utf-8'):
        # entity_level_goal = ""
        # count = 1
        data = json.loads(line.strip())
        # situation = data['situation']
        conversation = '\001'.join(data['history'])
        goals = data['goal']
        label = 0
        kg = data["knowledge"]
        user_profile = data["user_profile"]
        goals = goals.split('-->')
        dialog_flag = 'Bot'
        # current_entity_goal = ""

        # used_kg_entity = set()  # 背景知识中的s
        # for (s, r, o) in kg:
        #     if r != "适合吃" and s != '聊天':
        #         used_kg_entity.add(s)
        # used_kg_entity = list(used_kg_entity)
        #
        # user_profile_key_result = set()
        # for key in user_profile:
        #     user_profile_key_result.add(key)
        #
        # profile_entity_list = set()  # 用户画像中的value
        # for key in user_profile:
        #     if key.replace(' ', '') not in keyword_list:  # 存在空格的问题
        #         continue
        #     tmp_entity = user_profile[key]
        #     if isinstance(tmp_entity, list):
        #         for k in tmp_entity:
        #             profile_entity_list.add(k.strip())
        #     else:
        #         profile_entity_list.add(tmp_entity.strip())
        # profile_entity_list = list(profile_entity_list)

        # 对话类型（目标序列中的第一个）
        first_goal = goals[0].strip().split(']', 1)[-1].split('(', 1)[0].strip()
        final_goal = goals[-2].strip().split(']', 1)[-1].split('(', 1)[0].strip()
        max_round = goals[-1].strip().split('[', 1)[-1].split(']', 1)[0].strip()
        # if '......' in data['goal']:  # 存在省略的goal，提取......后面的那一个
        #     final_goal = goals[2].strip().split(
        #         ']', 1)[1].split('(', 1)[0].strip()
        # else:
        #     final_goal = goals[1].strip().split(
        #         ']', 1)[1].split('(', 1)[0].strip()

        if len(data['history']) > 0:
            first_utterance = data['history'][0]
        else:
            first_utterance = ''
        # try:
        #     first_utterance = data['history'][0]
        # except:
        #     first_utterance = ''
        name = user_profile['姓名']

        if first_utterance != last_utterance and last_kg != kg:  # 将同一个session的放在一起，“寒暄”？？？
            if begin_of_file == False:  # 排除文件开头
                output_file.write('\n')
            begin_of_file = False
        last_utterance = first_utterance
        last_kg = kg

        if first_goal in flag2:  # ["问答", "新闻 点播", "音乐 点播"]
            if '『 参考 知识 』' in data['goal']:
                first_goal_topic = data['goal'].strip().split(
                    '『 参考 知识 』')[-1].split('『 ', 1)[-1].split('』', 1)[0].strip()
            else:
                first_goal_topic = data['goal'].strip().split(
                    '『 ', 1)[-1].split('』', 1)[0].strip()
        else:
            first_goal_topic = first_goal

        if final_goal in flag3:  # "问 User 爱好", "天气 信息 推送"
            final_goal_topic = final_goal
        else:
            final_goal_topic = data['goal'].split(
                final_goal)[-1].split('『 ', 1)[-1].split('』', 1)[0].strip()
            if final_goal in flag4:  # "新闻 推荐"
                final_goal_topic += ' 新闻'  # 需要的嘛？
        # 对话内容+是否为一轮对话的开头(不是)+第一轮对话的类型+话题+最终对话的类型+话题+背景知识+用户画像+当前哪一方说话(Bot)
        output_file.write(conversation + '\t' + str(label) + '\t' + first_goal + '\t' + first_goal_topic + '\t' +
                          final_goal + '\t' + final_goal_topic + '\t' + str(kg) + '\t' + str(
            user_profile) + '\t' + dialog_flag + '\t' + max_round + '\n')

    output_file.close()


if __name__ == '__main__':
    add_label('../data/origin/train.txt', '../data/process/train_add_label.txt')
    add_label('../data/origin/dev.txt', '../data/process/dev_add_label.txt')
    process_session_data('../data/process/train_add_label.txt', '../data/process/train.txt')
    process_session_data('../data/process/dev_add_label.txt', '../data/process/dev.txt')
    process_test_data('../data/origin/test_1.txt', '../data/process/test.txt')
