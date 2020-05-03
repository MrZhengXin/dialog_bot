import json
import datetime
import re
import random


eq_relations = {
    '星座': [],
    '血型': [],
    '属相': ['属 啥', '属 什么', ],
    '成就': [],
    '主演': ['谁 演 的'],
    '类型': ['什么 歌'],
    '评论': [],  # ['唱 的 咋样', '评价', '好听 吗'],
    '导演': ['谁 导 的'],
    '简介': ['介绍', '信息'],
    '演唱': ['谁 唱 的', '主唱', '谁 的 歌'],
    '身高': ['多高', '多 高'],
    '体重': ['多重'],
    '获奖': ['哪些 奖', '什么 成就'],
    '口碑': [],
    '生日': ['什么 时候 出生', '哪 年 出生', '哪年 出生', '哪一年 出生', '的 出生 ', '出生日期', '多会 出生', '生日 是 多会'],
    '出生地': ['哪里 的 人', '哪儿 的 人', '哪里 出生', '在 哪 出生', '哪儿 出生', '哪 的', '哪里 的 籍贯', '哪里 人', '出生 地区', '出生 在 哪里'],
    '国家地区': ['国家 地区', '哪个 国家'],
    '人均价格': ['人均 价格', '消费 怎么样', '人均 消费', '平均价格'],
    '地址': ['在 哪', '具体位置'],
    '评分': [],
    '特色菜': [],
    '日期': [],  # '问 日期' in goal[0]
    '时间': [],  # '问 时间' in goal[0]
    '新闻': ['故事'],
    '天气': []
}
difficult_info_mask = {'身高': 'height', '体重': 'weight', '评分': 'rating', '地址': 'address', '人均价格': 'expense'}


def validate(date_text):
    try:
        datetime.datetime.strptime(date_text, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def check_relation(rel, qa):
    possible_rel = (eq_relations[rel] if rel in eq_relations.keys() else []) + [rel]
    for r in possible_rel:
        if r in qa:
            return True
    return False


def cal_score(triple, qa):
    score = 1 if triple[0] in qa else 0
    score += 1 if triple[1] in qa else 0
    if triple[2] in qa:
        score += 2
    else:
        common_words = [word for word in triple[3] if (word in qa and word not in ['', ' '])]
        if len(common_words) / len(triple[3]) > 0.4 or (len(common_words) > 0 and triple[1] in ['评论', '出生地']):
            score += 2

    return score


def remove_marks(x):
    return x.replace(' ', '').replace('（', '').replace('）', '')


random.seed()
with open('test_1.json', 'r') as f:
    x = f.readlines()

with open('test_1_goal_fill.txt', 'r') as f:
    goals_info = f.readlines()
    goals_info = [eval(i) for i in goals_info]

src = open('test_with_knowledge.src', 'w')

num = -1
news_dict = dict()
mask_info = dict()
entity_dicts = dict()
questions = []
for i in x:
    num += 1
    # i = i.replace(' ', '')
    i = json.loads(i)
    goal = i['goal'].split('-->')

    if len(i['history']) == 0:
        hello_info = ['寒暄', i['situation']]
        if '带 User 名字' in goal[0]:
            hello_info.append(i['user_profile']['姓名'])
            hello_info.append(i['user_profile']['性别'])
            if '年龄区间' in str(i['user_profile']):
                hello_info.append(i['user_profile']['年龄区间'])
        print(hello_info, file=src)
        continue

    if len(i['history']) == 1 and ('问 时间' in goal[0] or '问 日期' in goal[0]):
        print(i['situation'], i['history'][0], file=src)
        continue


    goal = goals_info[num]
    kg = i['knowledge']
    # fix bug when song contain "   "
    for j in range(len(kg)):
        if kg[j][1] != '评论' and '评论' in kg[j][1]:
            kg[j][0] += ' ' + kg[j][1].replace(' 评论', '')
            kg[j][1] = '评论'
    conversation = ' '.join(i['history'])
    current_goal_stage = len(re.findall('\[[1-9]\]', conversation))
    current_round = 0
    for u in i['history'][::-1]:
        # if goal[current_goal_stage-1][1] == '关于 明星 的 聊天':
            # print(u)
        current_round += 1
        if u[0] == '[':
            break
    # if goal[current_goal_stage-1][1] == '关于 明星 的 聊天':
        # print(current_goal_stage, current_round)
    history = ' '.join(i['history'][:-1])
    question = i['history'][-1]
    # if question[0] == '[':
        # question = question[4:]




    # find replace entity
    entity_cnt = 0
    entity_dict = dict()
    recommend_entity = ''
    for g in goal:
        if len(g) < 2:
            continue
        action = g[1]
        if action == '兴趣点 推荐':
            entity_dict[g[2]] = 'restaurant_' + str(entity_cnt)
            entity_cnt += 1
            continue
        if action in ['电影 推荐', '音乐 推荐']:

            for r in g[2]:
                entity_dict[r] = ('movie_' if action == '电影 推荐' else 'song_') + str(entity_cnt)
                entity_cnt += 1
            continue

    # add goal transition
    goal_transition = goal[current_goal_stage - 1:current_goal_stage + 1]
    if '新闻' in goal_transition[0][1]:
        goal_transition[0][3] = ''
    if len(goal_transition) > 1 and '新闻' in goal_transition[1][1]:
        goal_transition[1][3] = ''
    goal_transition = str(goal_transition)

    # chat about celebrity         :
    if (goal[current_goal_stage-1][1] == '关于 明星 的 聊天' and current_round < 4) or (goal[current_goal_stage-1][1] == '问答' and current_round > 2 and goal[current_goal_stage][1] == '关于 明星 的 聊天'):
        achievemnt_cnt = 0
        celebrity = goal[current_goal_stage - 1][2] if goal[current_goal_stage-1][1] == '关于 明星 的 聊天' else \
            goal[current_goal_stage][2]
        for k in kg:
            if achievemnt_cnt > 1:
                break
            entity, relation, info = k
            if entity == celebrity and relation == '成就' and info not in conversation:
                print(k, end='\t', file=src)
                achievemnt_cnt += 1
        print(question, file=src)
        continue
    # recommend movie, song, restaurant
    recommend_movie, recommend_song, recommend_restaurant, broadcast_news = '', '', '', []
    for g in goal[current_goal_stage - 1:current_goal_stage + 2]:  # search the first entity not appeared in conversation
        # from the current goal and the next goal
        if len(recommend_song) + len(recommend_movie) + len(recommend_restaurant) != 0:
            break
        action = g[1]
        if action == '兴趣点 推荐' and remove_marks(g[2]) not in remove_marks(conversation):
            recommend_restaurant = g[2]
            recommend_entity = entity_dict[recommend_restaurant]
        if action in ['电影 推荐', '音乐 推荐']:
            for r in g[2]:
                if remove_marks(r) not in remove_marks(conversation):
                    if action == '电影 推荐':
                        recommend_movie = r
                        recommend_entity = entity_dict[r]
                        break
                    else:
                        recommend_song = r
                        recommend_entity = entity_dict[r]
                        break

        if action in ['新闻 推荐', '新闻 点播']:
            news_of, news = g[2], g[3]
            news_words = set(news.split(' '))
            conversation_words = set(conversation.split(' '))
            appear_ratio = len(news_words.intersection(conversation)) / len(news_words)

            if appear_ratio < 0.18:
                broadcast_news = [news_of, '新闻', news]
                break

    using_k = set()
    max_knowledge = 3

    comment = ''
    for j in range(len(kg)):


        if max_knowledge == 0:
            break
        if kg[j][1] == '评论' and len(kg[j][2]) > 64:
            kg[j][2] = kg[j][2][:64]
        if (kg[j][0].replace(' ', '') in [recommend_movie.replace(' ', ''), recommend_song.replace(' ', '')] and kg[j][1] == '评论' and comment == '') or \
                (kg[j][0].replace(' ', '') == recommend_restaurant.replace(' ', '') and kg[j][1] == '特色菜' and kg[j][2] in conversation):

            kg[j][0] = recommend_entity
            comment = kg[j]

        if kg[j][1] == '新闻':  # news knowledge is already handled
            continue
        if str(kg[j]) in using_k:
            continue

        if check_relation(kg[j][1], question) and kg[j][0] != i['user_profile']['姓名'] and\
                (((kg[j][0].replace(' ', '') in conversation.replace(' ', '')) or (kg[j][2].replace(' ', '') in conversation.replace(' ', ''))) or \
                 ((kg[j][0].replace(' ', '') in conversation.replace(' ', '')) and kg[j][2].isdigit())):
            if kg[j][0] in entity_dict.keys():
                kg[j][0] = entity_dict[kg[j][0]]
            using_k.add(str(kg[j]))
            # if kg[j][1] == '新闻':
                # news[num] = kg[j][2]
            # digits = re.findall('[0-9.]*', kg[j][2])
            # print(digits)
            if kg[j][1] in difficult_info_mask.keys():
                mask = difficult_info_mask[kg[j][1]]
                if num not in mask_info.keys():
                    mask_info[num] = dict()
                mask_info[num][mask] = ' ' + kg[j][2] + ' '
                kg[j][2] = mask
            print(kg[j], end='\t', file=src)
            max_knowledge -= 1
        else:

            if ('天气' in question and validate(kg[j][1])) or \
                    ('适合' in kg[j][1] and len(i['history']) == 3) or \
                    ('生日' == kg[j][1] and goal[0][1] == '问 日期' and len(i['history']) == 3):
                using_k.add(str(kg[j]))
                if '天气' in question:
                    news_dict[num] = ('今天天气' if j & 1 else '今天') + kg[j][2].replace('~', '转')
                print(kg[j], end='\t', file=src)
                max_knowledge -= 1

    # replace entity in diaglog
    for j in range(len(i['history'])):
        for entity, entity_no in zip(entity_dict.keys(), entity_dict.values()):
            i['history'][j] = i['history'][j].replace(entity, entity_no)

    question = i['history'][-1]
    if max_knowledge == 3:
        if recommend_movie != '' or recommend_song != '' or recommend_restaurant != '' or broadcast_news != []:
            print(comment if broadcast_news == [] else broadcast_news, end='\t', file=src)
        elif '再见' not in question and '拜拜' not in question:

            add_history = ''  # append history
            pos_h = len(i['history']) - 2
            while len(add_history + i['history'][pos_h]) < 128 and pos_h >= 0:
                add_history += i['history'][pos_h] + ' '
                pos_h -= 1

            print(add_history, end='\t', file=src)
            # if question[-1] == '？':
                # print(question)
    print(question, file=src)
    questions.append(question)
    entity_dicts[num] = str(entity_dict)


with open('test_hypo_entity (2).txt', 'r') as f:
    x = f.readlines()

gg = open('mbart_knowledge_input_no_history_entity_0502.txt', 'w')
for i in range(len(x)):
    x[i] = x[i].strip()
    x[i] = x[i].replace(',', ',').replace('?', '？').replace('!', '！').replace('°C', '℃').\
        replace('(', '（').replace(')', '）')
    # if i in news_dict.keys():
        # x[i] = news_dict[i]
    # if -i in news_dict.keys():
        # x[i] += news_dict[-i]

    if i in mask_info.keys():
        for key, value in zip(mask_info[i].keys(), mask_info[i].values()):
            # print(key, value)
            x[i] = x[i].replace(key, value)
    if i in entity_dicts.keys():
        entity_dict = eval(entity_dicts[i])

        song_0 = None
        for key, value in zip(entity_dict.keys(), entity_dict.values()):
            # print(key, value)
            x[i] = x[i].replace(value, key)
            if key == 'song_0':
                song_0 = value
        if 'song_1' in x[i] and song_0 is not None:
            x[i] = x[i].replace('song_1', song_0)
    print(x[i], file=gg)
