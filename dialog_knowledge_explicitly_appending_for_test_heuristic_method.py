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
    '生日': ['什么 时候 出生', '哪 年 出生', '哪年 出生', '哪一年 出生', '的 出生 ', '出生日期', '多会 出生'],
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

'''
def check_relation(relation, source):
    if relation in source or \
        ('多重' in source and relation == '体重') or \
            (('多高' in source or '多 高' in source) and relation == '身高') or \
            ('介绍' in source and relation == '简介') or \
        (('消费 如何' in source or '人均 消费' in source or '平均价格' in source) and relation == '人均价格') or \
        (('唱' in source or '谁 的 歌' in source) and relation == '演唱') or \
            ('在 哪' in source and relation == '地址') or \
            ('评价' in source and relation == '评论') or \
            (('哪年' in source or '出生' in source) and relation == '生日') or \
            ('时候' in source and relation == '时间') or \
            (('哪里' in source or '在 哪' in source or '出生 地区' in source or '哪 的' in source) and relation == '出生地'):
        return True
    return False
'''

random.seed()
with open('test_1.json', 'r') as f:
    x = f.readlines()

with open('next_goal(1).txt', 'r') as f:
    next_goal = f.readline()
    next_goal = eval(next_goal)

g = open('test_with_knowledge.src', 'w')

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
        print(hello_info, file=g)
        continue

    if len(i['history']) == 1 and ('问 时间' in goal[0] or '问 日期' in goal[0]):
        print(i['situation'], i['history'][0], file=g)
        continue



    kg = i['knowledge']

    # entity replace
    entity_cnt = 0
    entity_dict = dict()
    for gi in goal:
        gi_parts = gi.split('；')
        for gi_part in gi_parts:
            entity = re.findall('『[^』]*』', gi_part)
            if len(entity) == 0:
                continue
            entity = entity[0][1:-1].strip()
            entity_no = ''
            if '兴趣点 推荐' in gi:
                entity_no = 'restaurant_' + str(entity_cnt)
                entity_cnt += 1
            if '电影 推荐' in gi:
                entity_no = 'movie_' + str(entity_cnt)
                entity_cnt += 1
            if '播放 音乐' in gi:
                entity_no = 'song_' + str(entity_cnt)
                entity_cnt += 1
            if entity_no == '':
                continue
            entity_dict[entity] = entity_no
            for j in range(len(i['history'])):
                if entity in i['history'][j]:
                    i['history'][j] = i['history'][j].replace(entity, entity_no)
            for j in range(len(kg)):
                if kg[j][0].replace(' ', '') == entity.replace(' ', ''):
                    kg[j][0] = entity_no
                kg[j][2] = kg[j][2].replace(entity, entity_no)

    conversation = ' '.join(i['history'])
    history = ' '.join(i['history'][:-1])
    question = i['history'][-1]
    if question[0] == '[':
        question = question[4:]

    # news recommendations
    news_recommend = False
    for gi in goal:
        if '新闻 点播' not in gi and '新闻 推荐' not in gi:
            continue
        goal_num = re.findall('\[[1-9]\]', gi)[0]
        goal_num_previous = '[' + str(eval(goal_num[1])-1) + ']'
        if goal_num_previous != '[0]' and goal_num_previous not in conversation:
            break
        goal_num_next = '[' + str(eval(goal_num[1])+1) + ']'
        if goal_num_next in conversation:
            continue

        entity, news = re.findall('『[^』]*』', gi)
        news = news[1:-1]
        news = re.split("     |（", news)[0]
        entity = entity[1:-1]  # remove 『  』
        news_words = set(news.split(' '))
        conversation_words = set(conversation.split(' '))
        appear_ratio = len(news_words.intersection(conversation)) / len(news_words)

        if appear_ratio < 0.18:
            if '新闻 推荐' not in gi:
                news_dict[num] = news
            else:
                news_dict[-num] = news
            # news = '新闻'
            news_knowledge = [entity, '新闻', news]
            print(news_knowledge, question, file=g, sep='\t')
            # print(next_goal[num], question)
            news_recommend = True
            break
    if news_recommend:
        continue

    using_k = set()
    max_knowledge = 3
    play_song = ''
    recommend_movies = ''
    movie_comment = ''
    song_comment = ''

    # retrieve movie recommendation
    for gi in goal:
        if '电影 推荐' not in gi or recommend_movies != '':
            continue
        movies = re.findall('『[^』、]*』', gi)

        goal_num = re.findall('\[[1-9]\]', gi)[0]
        goal_num_previous = '[' + str(eval(goal_num[1])-1) + ']'
        if goal_num_previous != '[0]' and goal_num_previous not in conversation:
            break
        goal_num_next = '[' + str(eval(goal_num[1])+1) + ']'
        if goal_num_next in conversation:
            continue

        for movie in movies:
            movie = entity_dict[movie[1:-1].strip()]
            if movie not in conversation and recommend_movies == '':
                recommend_movies = movie
                break

    # retrieve music recommendation
    for gi in goal:
        if '播放 音乐' not in gi:
            continue

        goal_num = re.findall('\[[1-9]\]', gi)[0]
        goal_num_previous = '[' + str(eval(goal_num[1])-1) + ']'
        if goal_num_previous != '[0]' and goal_num_previous not in conversation:
            break
        goal_num_next = '[' + str(eval(goal_num[1])+1) + ']'
        if goal_num_next in conversation:
            continue

        play_song = re.findall('『[^』]*』', gi)[0][1:-1].strip()
        play_song = entity_dict[play_song]
        if play_song in question:
            break
        if play_song in conversation:
            play_song = ''  #already mentioned


    for j in range(len(kg)):
        if kg[j][1] == '演唱' and kg[j][0] not in entity_dict.keys():
            if 'song_0' not in entity_dict.values():
                entity_dict[kg[j][2]] = 'song_0'
            else:
                entity_dict[kg[j][2]] = 'song_1'

        if max_knowledge == 0:
            break
        if kg[j][0] in [recommend_movies, play_song] and kg[j][1] == '评论':
            comment = kg[j]
        if kg[j][1] == '新闻':  # news knowledge is already handled
            continue

        if kg[j][0] in entity_dict.keys():
            kg[j][0] = entity_dict[kg[j][0]]
        if kg[j][1] == '评论' and len(kg[j][2]) > 64:
            kg[j][2] = kg[j][2][:64]
        if check_relation(kg[j][1], question) and kg[j][0] != i['user_profile']['姓名'] and\
                (((kg[j][0].replace(' ', '') in conversation.replace(' ', '')) or (kg[j][2].replace(' ', '') in conversation.replace(' ', ''))) or \
                 ((kg[j][0].replace(' ', '') in conversation.replace(' ', '')) and kg[j][2].isdigit())):
            using_k.add(str(kg[j]))
            # if kg[j][1] == '新闻':
                # news[num] = kg[j][2]
            # digits = re.findall('[0-9.]*', kg[j][2])
            # print(digits)
            if kg[j][1] in difficult_info_mask.keys():
                mask = difficult_info_mask[kg[j][1]]
                if num not in mask_info.keys():
                    mask_info[num] = dict()
                mask_info[num][mask] = kg[j][2]
                kg[j][2] = mask
            print(kg[j], end='\t', file=g)
            max_knowledge -= 1
        else:
            if ('天气' in question and validate(kg[j][1])) or \
                    ('适合' in kg[j][1] and len(i['history']) == 3):
                using_k.add(str(kg[j]))
                if '天气' in question:
                    news_dict[num] = ('今天天气' if j & 1 else '今天') + kg[j][2].replace('~', '转')
                print(kg[j], end='\t', file=g)
                max_knowledge -= 1

    if max_knowledge == 3:
        if recommend_movies != '' or (play_song != '' and ('其他' in question or '推荐' in question or '别的' in question)):
            print(comment, end='\t', file=g)
        elif '再见' not in question and '拜拜' not in question:

            add_history = ''  # append history
            pos_h = len(i['history']) - 2
            while len(add_history + i['history'][pos_h]) < 128 and pos_h >= 0:
                add_history += i['history'][pos_h] + ' '
                pos_h -= 1

            print(add_history, end='\t', file=g)
            # if question[-1] == '？':
                # print(question)
            if '音乐推荐' == next_goal[num][0]:
                print(next_goal[num], question)
    print(question, file=g)
    questions.append(question)
    entity_dicts[num] = str(entity_dict)


with open('test_hypo_entity.txt', 'r') as f:
    x = f.readlines()

gg = open('mbart_knowledge_input_no_history_entity.txt', 'w')
for i in range(len(x)):
    x[i] = x[i].strip()
    x[i] = x[i].replace(',', ',').replace('?', '？').replace('!', '！')
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
'''

    if len(goal) == 0:
        continue

    user_first = True if 'User 主动' in goal[0] else False
    used_k = set()

    for j in range(len(conversation)-1):
        using_k = set()
        user_round = user_first ^ (j & 1)
        qa = conversation[j].strip() + ' ' + conversation[j + 1].strip()
        history = ' '.join(conversation[:j])
        for k in kg:
            if str(k) in used_k:
                continue
            score = cal_score(k, history + ' ' + conversation[j].strip(), conversation[j+1].strip())


            if score > max(1, cal_score(k, history, conversation[j].strip())):
                if user_round:
                    using_k.add(str(k[:3]))
                    if score > 2:
                        used_k.add(str(k[:3]))  # remove redundant tuple such as multiple celebrity birthday
        if len(using_k) != 0:
            print(*using_k, end='\t', file=g)
        print(conversation[j], file=g)
    print(conversation[-1], file=g)
    print(file=g)'''







