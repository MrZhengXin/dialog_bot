#!/usr/bin/env python
# -*- coding: utf-8 -*-
################################################################################
#
# Copyright (c) 2019 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
File: conversation_strategy.py
"""
from __future__ import print_function
from argparse import ArgumentParser
import json
import importlib

import sys

sys.path.append("../")
# from tools.convert_conversation_corpus_to_model_text import preprocessing_for_one_conversation
import dialog_test
from fairseq_cli.interactive import interactive_main, load_essential


importlib.reload(sys)
# sys.setdefaultencoding('utf8')


def load():
    """
    load model
    """
    parser = ArgumentParser()
    args = parser.parse_args()
    with open('commandline_args.txt', 'r') as f:
        args.__dict__ = json.load(f)

    models, use_cuda, task, src_dict, tgt_dict, generator, tokenizer, bpe = load_essential(args)

    return args, models, use_cuda, task, src_dict, tgt_dict, generator, tokenizer, bpe


def predict(args, models, use_cuda, task, src_dict, tgt_dict, generator, tokenizer, bpe, text):
    """
    predict
    """
    # return "ha ha ha"
    # print("success unpack")
    conversation, goal_info, kg, entity_dict, goal_transition, user_name, input_str = \
        dialog_test.process_input(text.strip())
    # print(input_str)
    # if isinstance(model_text, unicode):
        # model_text = model_text.encode('utf-8')

    response = interactive_main(args, models, use_cuda, task, src_dict, tgt_dict, generator, tokenizer, bpe, input_str)

    response = dialog_test.process_response(conversation, goal_info, kg, entity_dict, goal_transition, user_name, response)

    # topic_list = sorted(topic_dict.items(), key=lambda item: len(item[1]), reverse=True)
    # for key, value in topic_list:
        # response = response.replace(key, value)

    return response


def main():
    """
    main
    """
    args, models, use_cuda, task, src_dict, tgt_dict, generator, tokenizer, bpe = load()
    for line in sys.stdin:
        response = predict(args, models, use_cuda, task, src_dict, tgt_dict, generator, tokenizer, bpe, line.strip())
        print(response)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nExited from the program ealier!")
