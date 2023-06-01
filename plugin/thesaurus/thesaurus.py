import os
import re
import time
import random
from collections import defaultdict
import pandas as pd

import pickle
from transformers import BertTokenizer, BertModel
import torch
from sklearn.metrics import jaccard_score

from pycqBot import cqBot, cqHttpApi, Plugin, Message
from pycqBot.cqCode import node_list, node_list_alter
from pycqBot.data import Group_Message

# 当前插件路径
LOCAL_PATH = r'../plugin/thesaurus'
# 日志路径
LOG_PATH = '%s/data' % LOCAL_PATH

# 训练模型
MODEL_NAME = 'bert-base-chinese'
# 分词器
TOKENIZER = BertTokenizer.from_pretrained(MODEL_NAME)
# 编码
MODEL = BertModel.from_pretrained(MODEL_NAME)

# 训练数据的存储路径
DATA_SAVE_PATH = "%s/%s.pkl" % (LOG_PATH, MODEL_NAME)
# 训练词库路径
WORDS_PATH = '%s/depository' % LOG_PATH
# 训练词库路径
WORDS_FILE = 'thesaurus.csv'


# 加载词库
def load_data_set(file_list):
    """加载词库数据集"""
    data_path = '%s/%s' % (WORDS_PATH, WORDS_FILE)
    if os.path.isfile(data_path):
        data = pd.read_csv(data_path)
    else:
        # 存储每个文件的DataFrame
        dfs = []
        # 读取词库xls文件
        if not os.path.isdir(WORDS_PATH):
            os.makedirs(WORDS_PATH)
        for root, dirs, files in os.walk(WORDS_PATH):
            for file_path in files:
                # if file_path.endswith('.xls') or file_path.endswith('.xlsx'):
                if file_path in file_list:
                    df = pd.read_excel('%s/%s' % (WORDS_PATH, file_path),
                                       skiprows=1, usecols=[0, 1], names=['问题', '回答'])
                    dfs.append(df)

        # 合并多个DataFrame为一个数据集
        data = pd.concat(dfs, ignore_index=True)
        # 删除包含缺失值的行
        data.dropna(inplace=True)
        # 问题库和回答库
        qa_library = defaultdict(list)
        for _i, row in data.iterrows():
            question, answer = row['问题'], row['回答']
            qa = qa_library[question]
            if answer not in qa:
                qa.append(answer)

        data = pd.DataFrame(list(qa_library.items()), columns=['问题', '回答'])
        # 保存词库文件
        data.to_csv(data_path, index=False)

    return data['问题'].tolist(), data['回答'].tolist()


# 训练模型
def training_model(questions, answers):
    """训练模型"""
    if os.path.isfile(DATA_SAVE_PATH):
        # 加载存储的数据
        try:
            with open(DATA_SAVE_PATH, 'rb') as f:
                return pickle.load(f)
        except Exception:
            pass

    # 加载预训练的BERT模型和分词器
    model_name = MODEL_NAME
    tokenizer = TOKENIZER
    model = MODEL

    # 预处理问题
    encoded_library = tokenizer(questions[:], padding=True, truncation=True, return_tensors='pt')

    # 将预处理结果转移到GPU（如果可用）
    if torch.cuda.is_available():
        encoded_library = {k: v.to('cuda') for k, v in encoded_library.items()}

    # 获取问题的输出
    with torch.no_grad():
        library_outputs = model(**encoded_library)

    # 保存到文件
    with open(DATA_SAVE_PATH, 'wb') as f:
        pickle.dump(library_outputs, f)

    return library_outputs


# 加载词库
QUESTIONS, ANSWERS = load_data_set(['可爱系词库.xls'])
# 模型
BERT_OUTPUTS = training_model(QUESTIONS, ANSWERS)

# 称呼
MASTER_NAME = '苟修金'
USER_NAME = '欧尼酱'


class thesaurus(Plugin):
    """
    thesaurus

    词库
    ---------------------------
    """

    def __init__(self, bot: cqBot, cqapi: cqHttpApi, plugin_config) -> None:
        super().__init__(bot, cqapi, plugin_config)

        # 预训练的分词器
        self.tokenizer = TOKENIZER
        # 预训练的BERT模型
        self.model = MODEL
        # 训练模型
        self.outputs = BERT_OUTPUTS

        # 加载自定义词库问题和回答
        self.questions = QUESTIONS
        self.answers = ANSWERS
        # 阈值
        self.threshold = True
        self.threshold_count = 0

        # 如果存在词库，则启用插件
        if self.outputs:
            # 词库处理方法
            self.bot.thesaurus = self.trigger_thesaurus

            # 定义装饰器
            def decorator(func):
                def wrapper(*args, **kwargs):
                    bot_class, group_message = args[0:2]
                    bot_class.thesaurus(group_message)
                    func(*args, **kwargs)

                return wrapper

            # 使用装饰器装饰方法 修改group事件
            cqBot._message_group = decorator(cqBot._message_group)

    def match_threshold(self, _query, _similarity_scores, _threshold=0.5):
        # 寻找最高得分
        max_score = torch.max(_similarity_scores)
        # 获取最高得分的索引列表
        max_score_indices = torch.nonzero(_similarity_scores == max_score).squeeze(1)
        # 存储匹配结果的列表
        matches = defaultdict(list)

        # 遍历最高得分的索引列表
        for idx in max_score_indices:
            # 获取匹配的问题
            question = self.questions[idx]
            # 获取匹配的答案
            answer = self.answers[idx]
            # 将匹配结果添加到列表中
            matches[question].extend(eval(answer))

        matches_question = None
        matches_answer = None
        matches_similarity = _threshold
        # 将文本转换为词集合
        words1 = _query.lower().split()[0]
        list1 = list(words1)
        set1 = set(list1)
        for question, answer in matches.items():
            words2 = question.lower().split()[0]
            list2 = list(words2)
            set2 = set(list2)

            # 计算Jaccard相似度
            if not set1 - set2:
                jaccard_similarity = len(set1) / len(set2)
            else:
                # 计算交集和并集的长度
                intersection = len(set1 & set2)
                union = len(set1 | set2)
                # 计算Jaccard相似度
                jaccard_similarity = intersection / union

            if jaccard_similarity > matches_similarity:
                matches_question = question
                matches_answer = answer
                matches_similarity = jaccard_similarity

        return matches_question, matches_answer

    def trigger_thesaurus(self, message: Group_Message):
        """匹配回复"""
        if self.threshold is False:
            if self.threshold_count < 15:
                self.threshold_count += 1
                return
            else:
                self.threshold_count = 0

        self.threshold = False

        # 输入查询问题
        inputs = self.extract_string(message.message)

        if inputs.startswith('#'):
            return None

        # 预处理输入问题
        encoded_input = self.tokenizer(inputs, padding=True, truncation=True, return_tensors='pt')

        # 将预处理结果转移到GPU（如果可用）
        if torch.cuda.is_available():
            encoded_input = {k: v.to('cuda') for k, v in encoded_input.items()}

        # 进行推断
        with torch.no_grad():
            input_outputs = self.model(**encoded_input)

        # 计算相似度
        similarity_scores = torch.cosine_similarity(input_outputs.last_hidden_state.mean(dim=1),
                                                    self.outputs.last_hidden_state.mean(dim=1), dim=1)

        # # 获取最相似问题的索引
        # most_similar_index = torch.argmax(similarity_scores).item()
        # 最佳匹配阈值
        try:
            best_question, best_answer = self.match_threshold(inputs, similarity_scores)
            self.reply_string(message, best_question, best_answer)
        except Exception:
            ...
        finally:
            time.sleep(3)
            self.threshold = True
            self.threshold_count = 0

        # res = ("===>输入问题:%s\n" % inputs +
        #        "匹配问题:%s\n" % self.questions[most_similar_index] +
        #        "匹配答案:%s\n" % self.answers[most_similar_index])
        #
        # self.cqapi.send_group_msg(message.sender.group_id, res)
        # print("===>输入问题:", inputs,
        #       "匹配问题:", self.questions[most_similar_index],
        #       "匹配答案:", self.answers[most_similar_index])

        # # 获取最相似问题对应的回答
        # most_similar_answer = answers[most_similar_index]

        # # 输入查询问题
        # query = self.extract_string(message.message)
        # encoded_query = self.tokenizer.encode_plus(query, padding=True, truncation=True, return_tensors='pt')
        # query_inputs = {k: v.to('cpu') for k, v in encoded_query.items()}
        #
        # # 计算查询问题的编码表示
        # with torch.no_grad():
        #     query_outputs = self.model(**query_inputs)
        #
        # # 计算相似度
        # similarity_scores = torch.cosine_similarity(query_outputs.last_hidden_state.mean(dim=1),
        #                                             self.bert_pkl.last_hidden_state.mean(dim=1))
        # # 最佳匹配阈值
        # best_question, best_answer = self.match_threshold(query, similarity_scores)
        #
        # self.reply_string(message, best_question, best_answer)

    @staticmethod
    def extract_string(input_string):
        """格式化处理文本"""
        pattern = r'\[.*?\]'  # 匹配方括号内的内容
        result = re.sub(pattern, '', input_string)  # 去除方括号内的内容
        return result

    def reply_string(self, message: Group_Message, question, answer):
        """处理回复逻辑"""
        if not answer:
            return

        group_id = message.sender.group_id
        user_id = message.sender.id

        # 获取回复内容
        reply = answer[int(len(answer) * random.random() // 1)]

        # {me}替换成ai对自己的称呼
        # {name}替换为ai对聊天对象的称呼
        # {segment}为切分句子的标识
        reply = reply.replace('{me}', self.cqapi.bot_name). \
            replace('{name}', MASTER_NAME if user_id in self.bot.admin else USER_NAME). \
            split('{segment}')

        # self.cqapi.send_group_msg(group_id, '匹配提问：%s' % question)
        for _reply in reply:
            if _reply:
                self.cqapi.send_group_msg(group_id, _reply)
                time.sleep(1)
