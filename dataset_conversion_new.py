'''
File: dataset_conversion.py

This file defines DatasetConversion class that helps convert between .txt files and dataset for training/testing.
Class instance can be generated by dc = DatasetConversion(directory_path, sep_by_type),
where sep_by_type is either 'word' or 'char' depending on whether you want to
treat each word (meaning the group of notes simultaneously being played at each timestep)
or each character (literally each character in the .txt string) as the unit of input.
'''

## import statements
import numpy as np

import sys
import os

import utils


## constants
SEPARATOR = chr(utils.NOTES_SIZE) # separator between each timestep in .txt file
DEFAULT_NUM_INPUT = 16 # default number of unit input to be inserted at once
DEFAULT_NUM_OUTPUT = 1 # default number of unit output to be taken at once

MIDI_EXTS = ['.mid', '.midi']
TXT_EXTS = ['.txt']

## class definition
class DatasetConversion(object):

    def __init__(self, directory_path='.', sep_by_type='word'):
        self.data_to_int = {} # dict{str : int}, mapping each unique data to an integer
        self.int_to_data = {} # dict{int : str}, reverse of data_to_int
        self.dir_path = directory_path
        if sep_by_type in ['word', 'char']:
            self.sep_by_type = sep_by_type
        else:
            # error
            print("Param sep_by_type should be specified as either 'word' or 'char'")
            exit(1)

    def midi_to_txt(self):
        '''
        Class function: midi_to_txt

        Input--
            None
        Output--
            None

        This file converts all MIDI files in the class directory into .txt files for compression.
        Format consistent with .txt files used in utils.py
        '''
        midifile_list = utils.get_files_by_ext(self.dir_path, MIDI_EXTS)

        for midifile in midifile_list:
            utils.midi_to_txt(midifile, input_dir=self.dir_path, output_dir=self.dir_path)

    def txt_to_dataset(self, input_window_size=None, output_window_size=None, step=1):
        '''
        Class function: txt_to_dataset

        Input--
            input_window_size (int) : number of inputs to be considered at a time
            output_window_size (int): number of outputs to be taken at a time
            window_step (int)       : size of interval between each window
        Output--
            Two np.ndarrays X, Y, of shape (n_examples, num_input, 1) to be fed to LSTM.

        This function takes in a directory of .txt files and converts the data to a dataset format for LSTM.
        '''
        num_input_size = DEFAULT_NUM_INPUT if input_window_size is None else input_window_size
        num_output_size = DEFAULT_NUM_OUTPUT if input_window_size is None else output_window_size

        # generates a list of all text files in the directory
        txtfile_list = utils.get_files_by_ext(self.dir_path, TXT_EXTS)

        # calculate the total amount of data per each feed
        total_size_per_feed = num_input_size + num_output_size

        # initialize
        extend_sz = 10000

        X = np.zeros((extend_sz, 128, num_input_size))
        Y = np.zeros((extend_sz, 128, num_output_size))
        file_example_start_idx = 0
        for file_cnt, file in enumerate(txtfile_list):
            # get the total path
            # print(file_cnt)

            filepath = os.path.join(self.dir_path, file)
            # print(filepath)
            with open(filepath, 'r', encoding='utf-8') as in_f:
                data = in_f.read()
                dataset = utils.str_to_np(data)

                num_examples = (dataset.shape[1] - total_size_per_feed) // step

                # file_example_start_idx = X.shape[0]
                # X = np.concatenate((X, np.zeros((num_examples, dataset.shape[0], num_input_size))), axis=0)
                # Y = np.concatenate((Y, np.zeros((num_examples, dataset.shape[0], num_output_size))), axis=0)

                for idx in range(num_examples):
                    # take the first num_input_size data as input
                    input_x = dataset[:, idx*step : idx*step + num_input_size]\
                              .reshape(1, dataset.shape[0], num_input_size)
                    # take the later num_output_size data as output
                    output_y = dataset[:, idx*step + num_input_size : idx*step + total_size_per_feed]\
                              .reshape(1, dataset.shape[0], num_output_size)

                    if file_example_start_idx + idx >= X.shape[0]:
                        X = np.concatenate((X, np.zeros((extend_sz, 128, num_input_size))))
                        Y = np.concatenate((Y, np.zeros((extend_sz, 128, num_output_size))))
                        extend_sz *= 2

                    X[file_example_start_idx + idx] = input_x
                    Y[file_example_start_idx + idx] = output_y

                file_example_start_idx += num_examples

        return X[:file_example_start_idx], Y[:file_example_start_idx]

    def dataset_to_str(self, Y):
        '''
        Class function: dataset_to_str

        Input--
            Y(np.ndarray) : shape (1, num_output_size, 1)
        Output--
            str : Y converted into a string format (consistent with utils.py)

        This function converts the output from LSTM to a text string format,
        so that they can subsequently be converted into MIDI files and played.
        '''
        # round the values to the nearest index assigned to vocabulary
        Y = np.around(Y * len(self.int_to_data))
        # make sure that they don't go out of MIDI range (0-127)
        Y = np.minimum(np.maximum(Y, 0), len(self.int_to_data) - 1)
        # flatten list
        Y = Y.flatten().tolist()
        # convert to text format
        Y_str = [self.int_to_data[Y[i]] for i in range(len(Y))]
        if self.sep_by_type == 'word':
            str_output = SEPARATOR.join(Y_str)
        elif self.sep_by_type == 'char':
            str_output = ''.join(Y_str)

        return str_output

    def str_to_midi(self, text_string, filename=None):
        '''
        Class function: str_to_midi

        Input--
            text_string (str) : string representation (consistent with utils.py) of MIDI notes
        Output--
            filename (str) : name of created MIDI file name

        This function convers our string representation of MIDI notes (likely outputted from model)
        to a playable .mid file.
        '''
        arr = utils.str_to_np(text_string)
        return utils.arr_to_midi(arr, filename)

