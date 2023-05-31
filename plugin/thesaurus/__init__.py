from . import thesaurus

# # 预训练模型
# import os
# import sys
#
# from collections import defaultdict
# import pickle
# import torch
# import pandas as pd
# from transformers import BertTokenizer, BertModel
#
# # 根目录
# ROOT_PATH = sys.path[0].replace('\\', '/')
# # 当前插件路径
# LOCAL_PATH = r'../plugin/thesaurus'
# # 日志路径
# LOG_PATH = '%s/data' % LOCAL_PATH
#
# # 训练模型路径
# MODEL_PATH = '%s/__model__' % LOG_PATH
# # 训练词库路径
# WORDS_PATH = '%s/depository' % LOG_PATH
#
# # 修改训练模型的路径
# os.environ["TRANSFORMERS_CACHE"] = MODEL_PATH
# # 训练模型
# MODEL_NAME = 'bert-base-chinese'
# # 训练数据的存储路径
# DATA_SAVE_PATH = "%s/%s.pkl" % (LOG_PATH, MODEL_NAME)
#
# """开始训练模型"""
#
# if not os.path.isfile(DATA_SAVE_PATH):
#     # 存储每个文件的DataFrame
#     dfs = []
#     # 读取词库xls文件
#     if not os.path.isdir(WORDS_PATH):
#         os.makedirs(WORDS_PATH)
#     for root, dirs, files in os.walk(WORDS_PATH):
#         for file_path in files:
#             # if file_path.endswith('.xls') or file_path.endswith('.xlsx'):
#             if file_path == '可爱系词库.xls':
#                 df = pd.read_excel('%s/%s' % (WORDS_PATH, file_path), skiprows=1, usecols=[0, 1], names=['问题', '回答'])
#                 dfs.append(df)
#
#     # 合并多个DataFrame为一个数据集
#     data = pd.concat(dfs, ignore_index=True)
#     # 删除包含缺失值的行
#     data.dropna(inplace=True)
#     # 问题库和回答库
#     qa_library = defaultdict(list)
#     for _i, row in data.iterrows():
#         if _i > 1000:
#             break
#
#         question, answer = row['问题'], row['回答']
#         qa = qa_library[question]
#         if answer not in qa:
#             qa.append(answer)
#
#     if qa_library:
#         # 加载预训练的BERT模型和分词器
#         model_name = MODEL_NAME
#         tokenizer = BertTokenizer.from_pretrained(model_name)
#         model = BertModel.from_pretrained(model_name)
#
#         # 获取问题和回答
#         questions = list(qa_library.keys())
#         answers = list(qa_library.values())
#
#         # 预处理问题
#         encoded_library = tokenizer(questions, padding=True, truncation=True, return_tensors='pt')
#
#         # 将预处理结果转移到GPU（如果可用）
#         if torch.cuda.is_available():
#             encoded_library = {k: v.to('cuda') for k, v in encoded_library.items()}
#
#         # 获取问题的输出
#         with torch.no_grad():
#             library_outputs = model(**encoded_library)
#
#         # # 保存到文件
#         # with open(DATA_SAVE_PATH, 'wb') as f:
#         #     pickle.dump(library_outputs, f)
#
#         """"""
#
#         # 输入问题
#         input_question = '你？'
#
#         for input_question in [
#             '你!', '我出门一趟，你乖乖的', '你不吃我了吗', '你:死了'
#         ]:
#
#             # 预处理输入问题
#             encoded_input = tokenizer(input_question, padding=True, truncation=True, return_tensors='pt')
#
#             # 将预处理结果转移到GPU（如果可用）
#             if torch.cuda.is_available():
#                 encoded_input = {k: v.to('cuda') for k, v in encoded_input.items()}
#
#             # 进行推断
#             with torch.no_grad():
#                 input_outputs = model(**encoded_input)
#
#             # 计算相似度
#             similarity_scores = torch.cosine_similarity(input_outputs.last_hidden_state.mean(dim=1),
#                                                         library_outputs.last_hidden_state.mean(dim=1), dim=1)
#
#             # 获取最相似问题的索引
#             most_similar_index = torch.argmax(similarity_scores).item()
#
#             # # 获取最相似问题对应的回答
#             # most_similar_answer = answers[most_similar_index]
#
#             print("===>输入问题:", input_question,
#                   "匹配问题:", questions[most_similar_index],
#                   "匹配答案:", answers[most_similar_index], )
