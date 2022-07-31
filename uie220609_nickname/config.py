import os


MAIN_PATH = os.path.dirname(os.path.abspath(__file__))
print(MAIN_PATH)
config = {
    'model_path': './checkpoint/model_best',
    'test_path': './data/test_data_on_noemotion.txt',  # test_data_on_noemotion  # test02
    'test_gen_path': './data/test_gen.txt',
    'batch_size': 16,
    'max_seq_len': 512,
    'model': 'uie-base',
}
