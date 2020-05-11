import json
import datetime
import re
import random

with open('test_1.json', 'r') as f:
    x = f.readlines()

f = open('test_1_goal_fill.txt', 'w')


def fill_goal(i):
    """
        fill the blanks of goals in the test
        Input: a json record
        Output: a list of what's missing in i
    """
    goal = i['goal'].split(' --> ')
    goal = [j.strip() for j in goal]
    if goal[2].startswith('[3] 再见'):  # goal is already complete
        return []

    # find entities
    kg = i['knowledge']
    conversation = i['history']
    songs = list()
    movies = list()
    restaurant = list()
    birthday_person = ''
    singer = ''
    news_of = ''
    news = ''
    actor = ''
    for j in kg:
        entity, relation, info = j
        if relation == '新闻':
            news_of, news = entity, info
        if relation == '演唱' and info not in goal[0]:
            if info not in songs:
                songs.append(info)
            singer = entity
        if relation == '生日':
            birthday_person = entity
        # However, there is a strange movie "20   30   40"
        if relation == '主演' and info.find('   ') == -1 and info not in goal[0] and info not in goal[1]:  # avoid sth like ["星月童话", "主演", "张国荣   常盘贵子"]
            if info not in movies:
                movies.append(info)
            actor = entity
        if relation == '地址':
            restaurant.append(entity)

    # goal sequence length is four
    if goal[2].startswith('[4] 再见'):
        goal_fill = [[2, '']]
        if goal[1].startswith('[3] 新闻 推荐'):  # (4):1 寒暄  2 提问  3 新闻 推荐
            goal_fill = [[2, '提问']]
        if goal[1].startswith('[3] 兴趣点 推荐'):  # (6):1 问 天气  2 美食 推荐  3 兴趣点 推荐
            goal_fill = [[2, '美食 推荐']]
        if goal[1].startswith('[3] 电影 推荐'):  # (12):1 问答  2 关于 明星 的 聊天  3 电影 推荐  or (13):1 问 日期  2 关于 明星 的 聊天  3 电影 推荐
            if goal[0].startswith('[1] 问答'):
                celebrity = re.findall('『[^』]*』', goal[0])[1][2:-2]
            else:
                celebrity = birthday_person
            goal_fill = [[2, '关于 明星 的 聊天', celebrity]]
        if goal[1].startswith('[3] 播放 音乐'):  # (22):1 音乐 点播  2 音乐 推荐  3 播放 音乐 (21):1 问 天气  2 音乐 推荐  3 播放 音乐
            play_song = re.findall('『[^』]*』', goal[1])[0][2:-2]
            songs.remove(play_song)
            songs = songs + [play_song]
            goal_fill = [[2, '音乐 推荐', songs]]
        return goal_fill

    # goal sequence is five
    if goal[2].startswith('[5] 再见'):
        if goal[1].startswith('[4] 新闻 推荐'):  #(3):1 寒暄  2 音乐 推荐  3 关于 明星 的 聊天  4 新闻 推荐
            celebrity = re.findall('『[^』]*』', goal[1])[0][2:-2]
            goal_fill = [[2, '音乐 推荐', songs], [3, '关于 明星 的 聊天', celebrity]]
        if goal[1].startswith('[4] 电影 推荐'):
            if goal[0].startswith('[1] 问答'):  # (9):1 问答  2 关于 明星 的 聊天  3 电影 推荐  4 电影 推荐
                celebrity = re.findall('『[^』]*』', goal[0])[1][2:-2]
                goal_fill = [[2, '关于 明星 的 聊天', celebrity], [3, '电影 推荐', movies]]
            if goal[0].startswith('[1] 问 日期'):  # (10):1 问 日期  2 关于 明星 的 聊天  3 电影 推荐  4 电影 推荐
                goal_fill = [[2, '关于 明星 的 聊天', birthday_person], [3, '电影 推荐', movies]]
            if goal[0].startswith('[1] 寒暄'):  # (11):1 寒暄  2 音乐 推荐  3 关于 明星 的 聊天  4 电影 推荐
                goal_fill = [[2, '音乐 推荐', songs], [3, '关于 明星 的 聊天', singer]]
        if goal[1].startswith('[4] 播放 音乐'):  # (19):1 问答  2 关于 明星 的 聊天  3 音乐 推荐  4 播放 音乐  (20):1 问 日期  2 关于 明星 的 聊天  3 音乐 推荐  4 播放 音乐
            play_song = re.findall('『[^』]*』', goal[1])[0][2:-2]
            songs.remove(play_song)
            songs = songs + [play_song]
            goal_fill = [[2, '关于 明星 的 聊天', singer], [3, '音乐 推荐', songs]]

        return goal_fill

    # goal sequence is six
    if goal[1].startswith('[5] 问 User 爱好'):  #(14):1 寒暄  2 问 User 姓名  3 问 User 性别  4 问 User 年龄  5 问 User 爱好
        goal_fill = [[2, '问 User 姓名'],  [3, '问 User 性别'],  [4, '问 User 年龄']]
    if goal[1].startswith('[5] 电影 推荐'):
        if news_of == '':  # (8):1 寒暄  2 提问  3 提问  4 关于 明星 的 聊天  5 电影 推荐
            goal_fill = [[2, '提问'], [3, '提问'], [4, '关于 明星 的 聊天', actor]]
        else:  # (7):1 寒暄  2 新闻 推荐  3 关于 明星 的 聊天  4 电影 推荐  5 电影 推荐
            goal_fill = [[2, '新闻 推荐', news_of, news], [3, '关于 明星 的 聊天', news_of], [4, '电影 推荐', movies]]
    if goal[1].startswith('[5] 播放 音乐'):  # (16):1 问 日期  2 关于 明星 的 聊天  3 电影 推荐  4 音乐 推荐  5 播放 音乐
        play_song = re.findall('『[^』]*』', goal[1])[0][2:-2]
        songs.remove(play_song)
        songs = songs + [play_song]
        if goal[0].startswith('[1] 问 日期') or goal[0].startswith('[1] 问答'):
            if goal[0].startswith('[1] 问 日期'):  # (16):1 问 日期  2 关于 明星 的 聊天  3 电影 推荐  4 音乐 推荐  5 播放 音乐
                celebrity = birthday_person
            else:  # (15):1 问答  2 关于 明星 的 聊天  3 电影 推荐  4 音乐 推荐  5 播放 音乐
                celebrity = re.findall('『[^』]*』', goal[0])[1][2:-2]
            goal_fill = [[2, '关于 明星 的 聊天', celebrity], [3, '电影 推荐', movies], [4, '音乐 推荐', songs]]
        if len(movies) != 0:  # (18):1 寒暄  2 电影 推荐  3 关于 明星 的 聊天  4 音乐 推荐  5 播放 音乐
            goal_fill = [[2, '电影 推荐', movies], [3, '关于 明星 的 聊天', actor], [4, '音乐 推荐', songs]]
        else:  # (17):1 寒暄  2 提问  3 关于 明星 的 聊天  4 音乐 推荐  5 播放 音乐
            goal_fill = [[2, '提问'], [3, '关于 明星 的 聊天', singer], [4, '音乐 推荐', songs]]
    return goal_fill


def extract_info_from_goal(goal):
    no = int(goal[1])
    if '] 再见' in goal:
        return [no, '再见']
    action = re.findall('][^(]*\(', goal)[0][2:-2]
    sth = re.findall('『[^』]*』', goal)
    sth = [s[2:-2] for s in sth]
    if action == '兴趣点 推荐':
        return [no, action, sth[0]]
    if action in ['新闻 点播', '新闻 推荐']:
        return [no, action, sth[0], sth[1]]
    if action in ['电影 推荐', '音乐 推荐']:
        movies = [sth[0]]
        if '；' in goal:
            movies.append(sth[3])
        return [no, action, movies]
    if action == '播放 音乐':
        return [no, action, sth[0]]
    if action == '关于 明星 的 聊天':
        return [no, action, sth[0]]
    return [no, action]


def fill_test(i):

    goals_fill = fill_goal(i)
    goals = i['goal']
    goals_info = [extract_info_from_goal(j) for j in goals.split(' --> ')]
    if len(goals_fill) == 0:
        return goals_info
    else:
        goals_info_complete = [goals_info[0]] + goals_fill + goals_info[1:]
        return goals_info_complete

