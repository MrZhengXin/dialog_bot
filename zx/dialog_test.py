import json
import nltk
import regex
import re
import datetime
import argparse
import goal_filling
import sacrebleu
import copy



actors = {'范冰冰', '黄晓明', '谢娜', '吴亦凡', '王力宏', '黄渤', '林心如', '杨幂', '周迅', '成龙', '刘若英', '舒淇', '张学友', '张柏芝', '刘德华', '郭富城', '周杰伦', '张国荣', '林志颖', '何炅', '谢霆锋'}

difficult_info_mask = {'身高': 'height', '体重': 'weight', '评分': 'rating', '地址': 'address', '特色菜': 'special',
                       '人均价格': 'expense', '导演': 'director', '姓名': 'name', '星座': 'constellation',
                       '血型': 'bloodtype', '出生地': 'birthplace', '生日': 'birthday', '国家地区': 'region', '属相': 'zodiac'}


with open('dialog_comment_recommends_merge.txt', 'r') as f:
    comment_recommends = f.readline()
    comment_recommends = eval(comment_recommends)
    select_comments_dict = comment_recommends.keys()

with open('dialog_celebrity_chat_merged.txt', 'r') as f:
    celebrity_chat = f.readline()
    celebrity_chat = eval(celebrity_chat)


def validate_date(date_text):
    try:
        datetime.datetime.strptime(date_text, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def ks_in_kg(ks, kg, conversation):
    ks = copy.deepcopy(ks)
    for k in kg:
        strk = str(k)
        if strk in ks:
            if k[1] not in ['成就', '获奖', '评价', '简介'] or k[2].replace(' ', '') in conversation.replace(' ', ''):
                return False
            ks.remove(strk)
    return len(ks) == 0


def decode_json(i):
    """
        decode the json, complete the goal if needed, enrich the goal,
        return conversation, goal information list, knowledge graph list and entity dict
        input:
            i: json
        output:
            conversation: list
            goal_info: list
            kg: list
            entity_dict: dictionary
    """
    mask_info = dict()
    conversation = i['history'] if 'history' in i.keys() else i['conversation']
    if len(conversation) > 0 and conversation[0][0] != '[':
        conversation[0] = '[1] ' + conversation[0]
    conversation = [c.replace(i['user_profile']['姓名'], 'name') for c in conversation]  # replace user's name
    goal = i['goal'].split('-->')
    if '......' in i['goal']:
        goal_info = goal_filling.fill_test(i)
    else:
        goal_info = [goal_filling.extract_info_from_goal(g) for g in goal]


    kg = i['knowledge']

    for j in range(len(kg)):
        if kg[j][1] == '生日':
            digits = kg[j][2].split('-')
            if len(digits) > 2:
                kg[j][2] = digits[0] + '年' + digits[1] + '月' + digits[2]
        if kg[j][1] == '出生地':
            kg[j][2] = kg[j][2].replace('   ', ' ')
        if kg[j][1] == '导演' and '   ' in kg[j][2]:
            kg[j][2] = kg[j][2].replace('   ', ' ， ')



    # entity replacement

    entity_cnt = 0
    entity_dict = dict()

    for gi in range(len(goal_info)):

        if goal_info[gi][1] == '音乐推荐':
            goal_info[gi][1] = '音乐 推荐'
        if goal_info[gi][1] == '美食推荐':
            goal_info[gi][1] = '美食 推荐'
        if goal_info[gi][1] == '兴趣点推荐':
            goal_info[gi][1] = '兴趣点 推荐'
        if goal_info[gi][1] == '电影推荐':
            goal_info[gi][1] = '电影 推荐'    
        if goal_info[gi][1] == '播放音乐':
            goal_info[gi][1] = '播放 音乐'  
        if goal_info[gi][1] == '音乐点播':
            goal_info[gi][1] = '音乐 点播' 
        if goal_info[gi][1] == '问时间':
            goal_info[gi][1] = '问 时间' 
        if goal_info[gi][1] == '问日期':
            goal_info[gi][1] = '问 日期'    
        if goal_info[gi][1] == '天气信息推送':
            goal_info[gi][1] = '天气 信息 推送'  
        if goal_info[gi][1] == '问天气':
            goal_info[gi][1] = '问 天气'     
        if goal_info[gi][1] == '关于明星的聊天':
            goal_info[gi][1] = '关于 明星 的 聊天'    

                
        if goal_info[gi][1] in ['问 时间', '问 日期']:  # add time in goal
            goal_info[gi].append(i['situation'])
            continue

        if goal_info[gi][1] in ['天气 信息 推送', '问 天气']:  # add weather in goal
            for k in kg:
                city, thedate, weather = k
                if validate_date(thedate):
                    goal_info[gi].append(city)
                    goal_info[gi].append(weather)
                    break
            continue
        if len(goal_info[gi]) != 3 or goal_info[gi][1] not in ['美食 推荐', '兴趣点 推荐', '电影 推荐', '播放 音乐', '音乐 推荐', '音乐 点播']:
            continue

        if goal_info[gi][1] == '播放 音乐':  # play the last recommend song
            goal_info[gi][2] = entity_dict[goal_info[gi][2]]
            continue

        entities = goal_info[gi][2] if type(goal_info[gi][2]) is type(list()) else [goal_info[gi][2]]
        goal_info_enrich = []
        entity_cnt += len(entities)

        # solve recuresive　name like 欺诈 的 碎片 与 惊心 的 情感 ： 《 色 · 戒 》 纪实 and 色 · 戒
        for entity in entities[::-1]:
            # no redundant entity
            if entity in entity_dict.keys():
                continue
            entity_no = ''
            if '美食 推荐' == goal_info[gi][1]:
                entity_cnt -= 1
                entity_no = 'special_' + str(entity_cnt)
            if '兴趣点 推荐' == goal_info[gi][1]:
                entity_cnt -= 1
                entity_no = 'restaurant_' + str(entity_cnt)
            if '电影 推荐' == goal_info[gi][1]:
                entity_cnt -= 1
                entity_no = 'movie_' + str(entity_cnt)
                has_acting_knowledge = False
                for k in kg:
                    if k[2] == entity and k[1] == '主演':
                        has_acting_knowledge = True
                        break
            if goal_info[gi][1] in ['音乐 推荐', '音乐 点播']:
                entity_cnt -= 1
                entity_no = 'song_' + str(entity_cnt)
            if entity_no == '':
                continue
            entity_dict[entity] = entity_no

            entity_appear = False
            for j in range(len(conversation)):
                if entity in conversation[j]:
                    entity_appear = True
                    conversation[j] = conversation[j].replace(entity, entity_no)



            comment_lists = list()
            used_comment, new_comment = '', ''
            info_lists = [entity_no]
            for j in range(len(kg)):
                if kg[j][0].replace(' ', '').replace('·', '') == entity.replace(' ', '').replace('·', ''):
                    if kg[j][0].replace(' ', '') + ':' == kg[j][2].replace(' ', ''):  # avoid comments like
                        # ["亚飞与亚基", "评论", "亚飞与亚基 :"]"
                        continue
                    if goal_info[gi][1] in ['音乐 推荐', '电影 推荐']:  # collect all comments to this entity
                        if len(kg[j][2]) > 4 and kg[j][1] == '评论' and used_comment == '':
                            kg[j][2] = kg[j][2][:88]
                            if str(kg[j]) in select_comments_dict:
                                used_comment = kg[j][2][:64]
                            elif new_comment == '':
                                new_comment = kg[j][2][:64]
                        if kg[j][1] in ['主演', '类型', '口碑']:
                            info_lists.append(kg[j][1:])
                    kg[j][0] = entity_no

            if type(goal_info[gi][2]) is type(str()):
                goal_info[gi][2] = entity_no
                continue
            # find which comment is used by calculate sacrebleu
            if goal_info[gi][1] in ['音乐 推荐', '电影 推荐']:

                info_lists.append(['评价', used_comment if used_comment != '' else new_comment])
                goal_info_enrich.append(info_lists)

                # print(entity_no, info_lists)
                # input()
        if len(goal_info_enrich) != 0:
            goal_info[gi][2] = goal_info_enrich[::-1]

        entity_cnt += len(entity_dict)

    return conversation, goal_info, kg, entity_dict


def process_input(i):

    i = json.loads(i)
    conversation, goal_info, kg, entity_dict = decode_json(i)
    goal = i['goal'].split('-->')

    if len(conversation) == 0 and '寒暄' in goal[0]:
        hello_info = ['寒暄', i['situation']]
        if '带 User 名字' in goal[0]:
            hello_info.append('name')
            hello_info.append(i['user_profile']['性别'])
            if '年龄区间' in str(i['user_profile']):
                hello_info.append(i['user_profile']['年龄区间'])
        return conversation, goal_info, kg, entity_dict, [goal_info[0]], i['user_profile']['姓名'], "φ".join(hello_info)
    else:
        # add goal transition
        current_goal_stage = max(len(set(re.findall('\[[1-9]\]', ''.join(conversation)))), 1)
        current_round = 0
        for c in conversation[::-1]:
            current_round += 1
            if c[0] == '[':
                break

        goal_transition = copy.deepcopy(goal_info[current_goal_stage - 1:current_goal_stage + 1])

        # add knowledge of celebrity to goal transition
        # chat about celebrity, add knowledge set that used in training set
        if (goal_transition[0][1] == '关于 明星 的 聊天' and current_round < 4) or \
                (1 < len(goal_transition) and current_round >= 2 and goal_transition[1][1] == '关于 明星 的 聊天'):
            pos = 0 if goal_transition[0][1] == '关于 明星 的 聊天' else 1
            celebrity = goal_transition[pos][2]
            chat = celebrity_chat[celebrity]
            for ks, r in zip(chat.keys(), chat.values()):
                ks = eval(ks)
                if ks_in_kg(ks, kg, ''.join(conversation)):
                    goal_transition[pos] += [eval(uk)[1:] for uk in ks]
                    # print(goal_transition)
                    break

        if '新闻' in goal_transition[0][1]:
            goal_transition[0][3] = goal_transition[0][3].replace(' ', '')[:128]
        if len(goal_transition) > 1 and '新闻' in goal_transition[1][1]:
            goal_transition[1][3] = goal_transition[1][3].replace(' ', '')[:128]
        
        input_str = 'φ'.join([str(gstr) for gstr in goal_transition])+'φ'
        j = len(conversation)
        if 0 < j :  # add history
            add_history = []
            pos_h = j - 1
            delta_goal_stage = 0
            while len(' '.join(add_history) + conversation[pos_h]) < 128 and pos_h >= 0:
                add_history.append(conversation[pos_h].strip()[:36])
                if conversation[pos_h][0] == '[':
                    add_history[-1] += 'φ'
                    delta_goal_stage += 1
                    if delta_goal_stage >= 2:
                        break
                pos_h -= 1
            # add_history = [c + ' 。' if c[-1] not in ['！', '？', '。'] else c for c in add_history]
            input_str += 'φ'.join(add_history[::-1])
        return conversation, goal_info, kg, entity_dict, goal_transition, i['user_profile']['姓名'], input_str 


def process_response(conversation, goal_info, kg, entity_dict, goal_transition, user_name, response):


    # fix goal mark problem
    if response[0] == '[' and response[1] != '1':
        response = (('[' + str(goal_transition[1][0]) + ']') if len(goal_transition) > 1 else '') \
                    + response[3:]

    # replace knowledge in response
    for k in kg:
        if k[1] in difficult_info_mask.keys():
            key, value = "'" + difficult_info_mask[k[1]], k[2]
            if k[0] not in actors and 'restaurant' not in k[0]:
                key = k[0] + key
            if False and '生日' == k[1] and ('生日' in response or '出生' in response):
                if '年' in response:
                    response = re.sub('[0-9 ]*年[0-9 ]月[0-9 ]*', k[2], response)
                else:
                    k[2] = k[2][6:]
                    response = re.sub('[0-9 ]*月 [0-9]*', k[2], response)
                continue

            response = response.replace(key, value)


    # replacce punctuation

    response = response.replace(',', '，').replace('?', '？').replace('!', '！').replace('°C', '℃')
    if '气温' in response:
        response = response.replace(' ， ', ' ,   ').replace('℃ 最', '℃ ,   最').replace('风 最', '风 ,   最')\
            .replace('好 ,   ', '好 ， ').replace('的 ,   ', '的 ， ').replace('嘿,   ', '嘿 ， ')


    # replace user name
    response = response.replace('name', user_name)

    # replace entity in response
    for entity, entity_no in zip(entity_dict.keys(), entity_dict.values()):
        response = response.replace(entity_no, entity)

    if 'movie_1' in response:
        for k in kg:
            if k[1] == '主演' and k[0] in actors:
                response.replace('movie_1', k[2])
                break

    response = response.replace("身高 'height ", '').replace(' 《 movie_1 》', '')
    return response


if __name__ == '__main__':

    with open(args.test_json, 'r') as f:
        x = f.readlines()

    src = open(args.test_source_file, 'w')
    tgt = open(args.test_target_file, 'w')

    with open('mbart_1.635.txt', 'r') as f:
        prv = f.readlines()


    with open(args.test_generate_file, 'r') as f:
        gen = f.readlines()

    for num, i in enumerate(x):
        i = json.loads(i)
        conversation, goal_info, kg, entity_dict = decode_json(i)
        goal = i['goal'].split('-->')

        def hello_info():

            hello_info = ['寒暄', i['situation']]
            if '带 User 名字' in goal[0]:
                hello_info.append('name')
                hello_info.append(i['user_profile']['性别'])
                if '年龄区间' in str(i['user_profile']):
                    hello_info.append(i['user_profile']['年龄区间'])
            print(*hello_info, file=src, sep=args.knowledge_sep, end='')
            print(args.knowledge_end, file=src)

        if len(conversation) == 0 and '寒暄' in goal[0]:
            hello_info()
        else:
            # add goal transition
            current_goal_stage = max(len(set(re.findall('\[[1-9]\]', ''.join(conversation)))), 1)
            current_round = 0
            for c in conversation[::-1]:
                current_round += 1
                if c[0] == '[':
                    break

            goal_transition = copy.deepcopy(goal_info[current_goal_stage - 1:current_goal_stage + 1])

            # add knowledge of celebrity to goal transition
            # chat about celebrity, add knowledge set that used in training set
            if (goal_transition[0][1] == '关于 明星 的 聊天' and current_round < 4) or \
                    (1 < len(goal_transition) and current_round >= 2 and goal_transition[1][1] == '关于 明星 的 聊天'):
                pos = 0 if goal_transition[0][1] == '关于 明星 的 聊天' else 1
                celebrity = goal_transition[pos][2]
                chat = celebrity_chat[celebrity]
                for ks, r in zip(chat.keys(), chat.values()):
                    ks = eval(ks)
                    if ks_in_kg(ks, kg, conversation):
                        goal_transition[pos] += [eval(uk)[1:] for uk in ks]
                        break

            if '新闻' in goal_transition[0][1]:
                goal_transition[0][3] = goal_transition[0][3].replace(' ', '')[:128]
            if len(goal_transition) > 1 and '新闻' in goal_transition[1][1]:
                goal_transition[1][3] = goal_transition[1][3].replace(' ', '')[:128]
            print(*goal_transition, end=args.knowledge_end, sep=args.knowledge_sep, file=src)
            j = len(conversation)
            if 0 < j and args.force_history:  # add history
                add_history = []
                pos_h = j - 1
                delta_goal_stage = 0
                while len(' '.join(add_history) + conversation[pos_h]) < args.max_history_length and pos_h >= 0:
                    add_history.append(conversation[pos_h].strip()[:36])
                    if conversation[pos_h][0] == '[':
                        add_history[-1] += args.goal_stage_sep
                        delta_goal_stage += 1
                        if delta_goal_stage >= args.max_goal_stage_in_history:
                            break
                    pos_h -= 1
                # add_history = [c + ' 。' if c[-1] not in ['！', '？', '。'] else c for c in add_history]
                print(*add_history[::-1], sep=args.conversation_sep, end=args.conversation_sep, file=src)
            print(file=src)

        if args.source_only:
            continue
        response = gen[num]


        # fix goal mark problem
        if response[0] == '[' and response[1] != '1':
            response = (('[' + str(goal_transition[1][0]) + ']') if len(goal_transition) > 1 else '') \
                       + response[3:]

        # replace knowledge in response
        for k in kg:
            if k[1] in difficult_info_mask.keys():
                key, value = "'" + difficult_info_mask[k[1]], k[2]
                if k[0] not in actors and 'restaurant' not in k[0]:
                    key = k[0] + key
                if False and '生日' == k[1] and ('生日' in response or '出生' in response):
                    if '年' in response:
                        response = re.sub('[0-9 ]*年[0-9 ]月[0-9 ]*', k[2], response)
                    else:
                        k[2] = k[2][6:]
                        response = re.sub('[0-9 ]*月 [0-9]*', k[2], response)
                    continue

                response = response.replace(key, value)


        # replacce punctuation

        response = response.replace(',', '，').replace('?', '？').replace('!', '！').replace('°C', '℃')
        if '气温' in response:
            response = response.replace(' ， ', ' ,   ').replace('℃ 最', '℃ ,   最').replace('风 最', '风 ,   最')\
                .replace('好 ,   ', '好 ， ').replace('的 ,   ', '的 ， ').replace('嘿,   ', '嘿 ， ')


        # replace user name
        response = response.replace('name', i['user_profile']['姓名'])

        # replace entity in response
        for entity, entity_no in zip(entity_dict.keys(), entity_dict.values()):
            response = response.replace(entity_no, entity)

        if 'movie_1' in response:
            for k in kg:
                if k[1] == '主演' and k[0] in actors:
                    response.replace('movie_1', k[2])
                    break

        response = response.replace("身高 'height ", '').replace(' 《 movie_1 》', '')
        print(response.strip(), file=tgt)

