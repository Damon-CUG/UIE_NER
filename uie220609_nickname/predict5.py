# import os
# os.environ['CUDA_VISIBLE_DEVICES'] = '' # 不使用GPU，使用CPU进行训练

from functools import partial

import paddle
from paddlenlp.datasets import load_dataset
from paddlenlp.transformers import AutoTokenizer
from paddlenlp.metrics import SpanEvaluator

from model import UIE
from utils import convert_example, reader, MODEL_MAP
from paddlenlp.utils.tools import get_span, get_bool_ids_greater_than

import json
from config import config
import re

from bert4keras.tokenizers import Tokenizer
import time


encoding_model = MODEL_MAP[config['model']]['encoding_model']
tokenizer = AutoTokenizer.from_pretrained(encoding_model)

BERT_DICT_PATH = '/mnt/Jupyter/bert/chinese_roberta_wwm_ext_L-12_H-768_A-12/vocab.txt'
tokenizer2 = Tokenizer(BERT_DICT_PATH, do_lower_case=True)
model = UIE.from_pretrained(config['model_path'])


@paddle.no_grad()
def predict(model, metric, data_loader):
    """
    Given a dataset, it evals model and computes the metric.
    Args:
        model(obj:`paddle.nn.Layer`): A model to classify texts.
        metric(obj:`paddle.metric.Metric`): The evaluation metric.
        data_loader(obj:`paddle.io.DataLoader`): The dataset loader which generates batches.
    """
    model.eval()
    metric.reset()
    res_span = []
    for batch in data_loader:
        input_ids, token_type_ids, att_mask, pos_ids, start_ids, end_ids = batch
        start_prob, end_prob = model(input_ids, token_type_ids, att_mask,
                                     pos_ids)
        pred_start_ids = get_bool_ids_greater_than(start_prob)
        pred_end_ids = get_bool_ids_greater_than(end_prob)
        for i in range(len(pred_start_ids)):
            if pred_start_ids[i]==[] or pred_end_ids[i]==[]:
                res_span.append((-1, -1))
                continue
            res_span.append((pred_start_ids[i][0], pred_end_ids[i][0]))
    return res_span

def do_pre(path_in):
    test_ds = load_dataset(
        reader,
        data_path=path_in,   # config['test_path']
        max_seq_len=config['max_seq_len'],
        lazy=False)
    test_ds = test_ds.map(
        partial(
            convert_example, tokenizer=tokenizer, max_seq_len=config['max_seq_len']))

    test_batch_sampler = paddle.io.BatchSampler(
        dataset=test_ds, batch_size=config['batch_size'], shuffle=False)
    test_data_loader = paddle.io.DataLoader(
        dataset=test_ds, batch_sampler=test_batch_sampler, return_list=True)

    metric = SpanEvaluator()
    res_span = predict(model, metric, test_data_loader)
    return res_span

def entites(res_span, path_in):
    res = []
    # res = [(18, 18), (15, 15), (15, 17), (17, 18), (17, 20), (17, 20), (-1, -1)]
    # path_in = config['test_gen_path']  # test_gen_path, test_path
    path_out = path_in.replace('.txt', '_res_p4.txt')
    f_in = open(path_in, 'r', encoding='utf-8')
    f_out = open(path_out, 'w', encoding='utf-8')
    count = 0
    
    entities = []    
    
    for line in f_in.readlines():
        if line == None or line == '\n' or len(line) == 0:
            continue
        json_line = json.loads(line[:-1])
        out_dict = {}
        out_dict['content'] = json_line['content']
        sequence = out_dict['content']
        if res_span[count] == (-1, -1):
            out_dict['res'] = []
            out_json = json.dumps(out_dict, ensure_ascii=False)
            f_out.write(out_json + '\n')
            res.append('None')
        else:
            start, end = res_span[count][0]-3, res_span[count][1]-3
            tokens = tokenizer(out_dict['content'], return_offsets_mapping=True)
            input_ids = tokens.data["input_ids"]
            # offset_mapping = tokens.data["offset_mapping"]
            # span_seq = input_ids[offset_mapping[start][0] + 1: offset_mapping[end][-1]]
            # span_seq_list2 = tokenizer.convert_ids_to_tokens(span_seq)
            tokenized_sequence = tokenizer.convert_ids_to_tokens(input_ids[start: end+1])
            
            tokenized_sequence_str = "".join(tokenized_sequence)
            if len(re.findall(r'[0-9a-zA-Z]', tokenized_sequence_str)) != 0:  # r'[0-9a-zA-Z+-#@]'
                pre_en = False
                now_en = False
                for j in range(len(tokenized_sequence)):
                    if j == 0:
                        if len(re.findall(r'[\u4e00-\u9fa5]', tokenized_sequence[j])) == 0:
                            now_en = True
                        pre_en = now_en
                        continue
                    if len(re.findall(r'[\u4e00-\u9fa5]', tokenized_sequence[j])) == 0:
                        now_en = True
                    else:
                        now_en = False
                    if len(tokenized_sequence[j])>2 and tokenized_sequence[j][:2]=='##':
                        tokenized_sequence[j] = tokenized_sequence[j][2:]
                        continue
                    if len(re.findall(r'[\u4e00-\u9fa5]', tokenized_sequence[j])) == 0 and pre_en:
                        tokenized_sequence[j] = ' ' + str(tokenized_sequence[j])
                    pre_en = now_en
                span = "".join(tokenized_sequence)
                sequence_lower = sequence.lower()
                res_a = sequence_lower.find(span)
                if res_a != -1:
                    res_b = sequence[res_a: res_a+len(span)+1]
                else:
                    res_b = ''
            else:
                tokens2 = tokenizer2.tokenize(line, maxlen=512)
                mapping = tokenizer2.rematch(line, tokens2)
                entities.append(
                    (mapping[start][0], mapping[end][-1])
                )
                res_list = tokens2[entities[-1][0]:entities[-1][1]+1]
                res_b = ''.join(res_list)            

            out_dict['res'] = res_b
            out_json = json.dumps(out_dict, ensure_ascii=False)
            f_out.write(out_json + '\n')
            res.append(res_b)
        count += 1
    f_in.close()
    f_out.close()
    print(count)
    return res

if __name__ == "__main__":
    start_time = time.time()
    path_in = config['test_path']  # test_gen_path, test_path
    res_span = do_pre(path_in)
    res = entites(res_span, path_in)
    print(res)
    print('done')
    print(time.time() - start_time)
