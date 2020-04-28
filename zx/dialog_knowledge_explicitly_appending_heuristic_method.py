import json
import nltk
import regex
import re
import datetime
import argparse

parser = argparse.ArgumentParser(description='input delimiter. [ks]xxx[ks]xxx[ke]xxx[gs]xxx[gs]')
parser.add_argument('--knowledge_sep', type=str, default='\t')
parser.add_argument('--knowledge_end', type=str, default='\t')
parser.add_argument('--goal_stage_sep', type=str, default='\t')
parser.add_argument('--bot_in_history', type=bool, default=True, help='whether bot response appear in history')
parser.add_argument('--force_history', type=bool, default=False, help='normally if knowledges were found, no history \
would needed')
parser.add_argument('--max_history_length', type=int, default=128)
parser.add_argument('--max_goal_stage_in_history', type=int, default=2)
parser.add_argument('--train_json', type=str, default='train.json')
parser.add_argument('--train_source_file', type=str, default='gpt2_train.src')
parser.add_argument('--train_target_file', type=str, default='gpt2_train.tgt')

args = parser.parse_args()


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


def cal_score(triple, q, a):
    '''
    calculate if the triple(entity, relation, something) appears in the questions and answer
    '''
    if len(triple[2]) == 0 or len(triple[3]) == 0:
        return 0  # something empty like ["异灵灵异-2002", "评论", ""]
    qa = q + ' ' + a
    score = 1 if triple[0] in qa.replace(' ', '') else 0  # left entity appears
    score += check_relation(triple[1], qa)  # relation appears
    if triple[2] in a:  # something directly appears
        score += 2
    else:
        common_words = [word for word in triple[3] if (word in a.split() and word not in ['', ' '])]  # match by word
        if (triple[1] not in ['成就', '获奖'] and len(common_words) / len(triple[3]) > 0.4) or (len(common_words) > 0 and triple[1] in ['评论', '出生地']):  # comments and birth places are more loose
            score += 2
        else:
            score -= 2

    return score


with open(args.train_json, 'r') as f:
    x = f.readlines()

src = open(args.train_source_file, 'w')
tgt = open(args.train_target_file, 'w')
len_src = 0
len_tgt = 0

difficult_info_mask = {'身高': 'height', '体重': 'weight', '评分': 'rating', '地址': 'address',
                       '人均价格': 'expense'}

for i in x:
    i = json.loads(i)
    conversation = i['conversation']
    goal = i['goal'].split('-->')
    kg = i['knowledge']

    # entity replacement

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

            for j in range(len(conversation)):
                if entity in conversation[j]:
                    conversation[j] = conversation[j].replace(entity, entity_no)
            for j in range(len(kg)):
                if kg[j][0].replace(' ', '') == entity.replace(' ', ''):
                    kg[j][0] = entity_no
                kg[j][2] = kg[j][2].replace(entity, entity_no)






    user_first = True if 'User 主动' in goal[0] else False
    bot_hello = False
    if '寒暄' in goal[0]:
        bot_hello = True
        hello_info = ['寒暄', i['situation']]
        if '带 User 名字' in goal[0]:
            hello_info.append(i['user_profile']['姓名'])
            hello_info.append(i['user_profile']['性别'])
            if '年龄区间' in str(i['user_profile']):
                hello_info.append(i['user_profile']['年龄区间'])
        print(*hello_info, file=src, sep=args.knowledge_sep, end='')
        print(args.knowledge_end, file=src)
        len_src += 1

    # add reverse knowledge
    for j in range(len(kg)):
        if kg[j][1] in ['生日', '演唱', '导演', '主演', '星座']:
            kg.append([kg[j][2], kg[j][1], kg[j][0]])

    for j in range(len(kg)):

        if validate(kg[j][1]):
            kg[j][1] = '天气'  # weather knowledge relation always in date form
        if kg[j][1] in ['评论']:
            kg[j].append(re.split('[！？，。]', kg[j][2]))  # result example ["高中 时候 很 喜欢 他 的 歌 ", " 后面 就 只是 关注 他 的 生活 了 。"]
        else:
            if kg[j][1] == '出生地':
                kg[j].append(kg[j][2].split('   '))  # input example ["谢娜", "出生地", "中国   四川   德阳   中 江"]
            else:
                kg[j].append(kg[j][2].split(' '))  # match by words

        for k in kg[j][3]:
            if k in ['', ' ', '，', '。', '！', '。', '~', '-'] or\
            (len(kg[j][2]) > 4 and len(k) < 4 and kg[j][1] in ['评论']):  # unhelpful in matching
                kg[j][3].remove(k)



    if len(goal) == 0:
        continue

    used_k = set()  # used string-format knowledge tuple in previous conversation

    goal_stage_milestone = set()
    for j in range(len(conversation)-1):
        if conversation[j][0] == '[':
            goal_stage_milestone.add(j)
            conversation[j] = conversation[j][4:]
        using_k = set()  # bot need these knowledge tuples to answer
        user_round = user_first ^ (j & 1)  # True if it were user speaking
        qa = conversation[j].strip() + ' ' + conversation[j + 1].strip()
        history = ' '.join(conversation[:j])
        for k in kg:
            if str(k) in used_k:  # assume that no knowledge will be used twice
                continue
            score = cal_score(k, history + ' ' + conversation[j].strip(), conversation[j+1].strip())


            if score > max(2, cal_score(k, history, conversation[j].strip())):  # this knowledge might appear and not appear before
                if k[1] in difficult_info_mask.keys() and k[2] in conversation[j+1]:
                    conversation[j+1] = conversation[j+1].replace(k[2], difficult_info_mask[k[1]])
                    # print(conversation[j+1])
                    k[2] = difficult_info_mask[k[1]]
                if user_round:  # we only need simulate bot
                    using_k.add(str(k[:3]))  # using sest to remove redundant tuple such as multiple celebrity birthday
                if score > 3:
                    used_k.add(str(k[:3]))  # the knowledge is fully explored
                    #  consider the celebrity birthday cases.
                    #  First, the date today is asked and answered. However,
                    #  the celebrity birthday tuple would also be partially matched.
                    #  So the tuple cannot be treated as used knowledge.

        if j == 0 and ('问 日期' in goal[0] or '问 时间' in goal[0]):  # situation not in knowledge
            using_k = {i['situation']}

        if user_round:
            if len(using_k) != 0:
                print(*using_k, sep=args.knowledge_sep, end='', file=src)  # knowledge at the beginning of user question
            print(args.knowledge_end, end='', file=src)
            if 0 < j < len(conversation) - 2 and (len(using_k) == 0 or args.force_history):  # say good bye need not history information
                add_history = []
                pos_h = j - 1
                delta_goal_stage = 0
                while len(' '.join(add_history) + conversation[pos_h]) < args.max_history_length and pos_h >= 0:
                    add_history.append(conversation[pos_h].strip())
                    pos_h -= 1
                    if pos_h in goal_stage_milestone:
                        add_history[-1] += args.goal_stage_sep
                        delta_goal_stage += 1
                        if delta_goal_stage >= args.max_goal_stage_in_history:
                            break

                print(*add_history, sep='\t', end='\t', file=src)
        print(conversation[j] + args.goal_stage_sep, file=src if user_round else tgt)
        if user_round:
            len_src += 1
        else:
            len_tgt += 1
    if len_tgt == len_src - 1:
        print(conversation[-1], file=tgt)  # when bot say goodbye first, user's goodbye would be ignored.
        len_tgt += 1
    assert len_src == len_tgt
