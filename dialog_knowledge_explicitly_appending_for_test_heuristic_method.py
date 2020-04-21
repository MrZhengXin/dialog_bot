import json
import datetime


def validate(date_text):
    try:
        datetime.datetime.strptime(date_text, '%Y-%m-%d')
        return True
    except ValueError:
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


def check_relation(relation, source):
    if relation in source or \
        ('多重' in source and relation == '体重') or \
        ('介绍' in source and relation == '简介') or \
        (('消费如何' in source or '人均消费' in source) and relation == '人均价格') or \
        ('主唱' in source and relation == '演唱') or \
        (('哪里出生' in source or '哪里人' in source or '哪里的人' in source or '出生在哪里' in source or '哪的人' in source) and relation == '出生地'  ):
        return True
    return False

with open('test_1.json', 'r') as f:
    x = f.readlines()


g = open('test_with_knowledge.source', 'w')

num = -1
news = {}
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

    if len(i['history']) == 1 and '问时间' in goal[0]:
        print(i['situation'], i['history'][0], file=g)
        continue

    conversation = ''.join(i['history'])
    history = ''.join(i['history'][:-1])
    question = i['history'][-1]

    kg = i['knowledge']
    using_k = set()
    max_knowledge = 3
    for j in range(len(kg)):
        if max_knowledge == 0:
            break
        if kg[j][1] == '新闻':  # Paste the news later
            kg[j][2] = '纽斯'
        # if len(kg[j][2]) > 64:
            # kg[j][2] = kg[j][2][:64]
        if check_relation(kg[j][1], question) and kg[j][0] != i['user_profile']['姓名'] and ((kg[j][0] in conversation) ^ (kg[j][2] in conversation)):
            using_k.add(str(kg[j]))
            if kg[j][1] == '新闻':
                news[num] = kg[j][2]
            print(kg[j], end='\t', file=g)
            max_knowledge -= 1
        else:
            if ('天气' in question and validate(kg[j][1])) or \
                    (('几号' in question or '什么日子' in question) and kg[j][1] == '日期') or \
                    ('适合' in kg[j][1] and len(i['history']) == 3):
                using_k.add(str(kg[j]))
                if '天气' in question:
                    news[num] = kg[j][2]
                print(kg[j], end='\t', file=g)
                max_knowledge -= 1
    print(question, file=g)
