# coding=utf-8

import os
import sys

curpath = os.path.dirname(os.path.realpath(__file__))

g_data_matrix = [
    [111, 'aaa', 'nnn'],
    [111, 'bbb', 'mmm'],
    [222, 'ccc', 'xxx'],
    [333, 'ddd', 'yyy'],
]


def matrix_2_bytes(matrix):
    return b'\n'.join([b'\t'.join(map(bytes, row)) for row in matrix])


g_data = matrix_2_bytes(g_data_matrix)

g_column_names = [u'column_0', u'column_1', u'column_2']

import pandas as pd
from io import BytesIO

import unittest


class MyTestCase(unittest.TestCase):
    def _make_gzip(self):
        import gzip
        out_stream = BytesIO()
        with gzip.GzipFile(fileobj=out_stream, mode='wb') as f:
            f.write(g_data)
        return BytesIO(out_stream.getvalue())

    def _dataframe_equal_matrix(self, chunk, matrix, maxtrix_column_names):

        self.assertEqual(maxtrix_column_names, chunk.columns.values.tolist())

        rows_count = len(matrix)
        self.assertEqual(rows_count, len(chunk))

        # check columns
        for col_idx in range(len(matrix[0])):
            col = [row[col_idx] for row in matrix]
            v = chunk[maxtrix_column_names[col_idx]].tolist()
            self.assertEqual(col, v)

        # check rows

        rows_iter = chunk.iterrows()
        for row_idx, row in enumerate(matrix):
            v = rows_iter.next()
            # row_idx 不一定是连续的 如果被 drop 过，就不是连续的
            # self.assertEqual(row_idx, v[0])
            self.assertEqual(row, v[1].tolist())

    def _basic_read(self):
        return pd.read_csv(BytesIO(g_data),
                           names=g_column_names,
                           header=None,
                           sep='\t')

    def test_basic(self):

        chunk = self._basic_read()

        self._dataframe_equal_matrix(chunk, g_data_matrix, g_column_names)

    def test_read_as_iter(self):
        chunk1 = pd.read_csv(BytesIO(g_data),
                             names=g_column_names,
                             header=None,
                             sep='\t',
                             iterator=True,
                             chunksize=10,
                             engine='c')
        l = list(chunk1)
        self.assertEqual(1, len(l))
        self._dataframe_equal_matrix(l[0], g_data_matrix, g_column_names)

        chunk2 = pd.read_csv(BytesIO(g_data)
                             , names=g_column_names
                             , header=None
                             , sep='\t'
                             , iterator=True
                             , chunksize=1
                             # ,engine='c' # have or not is all work
                             )

        l2 = list(chunk2)

        self.assertEqual(4, len(l2))

        self._dataframe_equal_matrix(
            l2[0], [[111, 'aaa', 'nnn']], g_column_names
        )

    def test_read_from_gzip(self):
        chunk = pd.read_csv(self._make_gzip(),
                            names=g_column_names,
                            header=None,
                            sep='\t',
                            compression='gzip',  # default 'infer' 如果是文件路径，从文件后缀推断
                            # engine='python',  #  python or c
                            )

        self._dataframe_equal_matrix(chunk, g_data_matrix, g_column_names)

    def test_drop_duplicates(self):

        chunk = self._basic_read()

        # 按照某一列 去重复
        chunk2 = chunk.drop_duplicates(g_column_names[0])

        self._dataframe_equal_matrix(
            chunk2,
            [
                [111, 'aaa', 'nnn'],
                [222, 'ccc', 'xxx'],
                [333, 'ddd', 'yyy'],
            ], g_column_names
        )

    def test_drop_nan(self):
        import math
        local_data = b'''\
        111\taaa\t
        222\t\tmmm
        333\tccc\txxx
        '''
        chunk = pd.read_csv(BytesIO(local_data),
                            names=g_column_names,
                            header=None,
                            sep='\t')

        chunk2 = chunk[pd.notnull(chunk[g_column_names[1]])]

        # there is also have Nan in column[2]
        chunk2 = chunk2.fillna('')

        self._dataframe_equal_matrix(
            chunk2,
            [
                [111, 'aaa', ''],
                [333, 'ccc', 'xxx']
            ], g_column_names
        )

        chunk3 = chunk[pd.notnull(chunk[g_column_names[2]])]
        chunk3 = chunk3.fillna('')

        self._dataframe_equal_matrix(
            chunk3,
            [
                [222, '', 'mmm'],
                [333, 'ccc', 'xxx'],
            ], g_column_names
        )

    def test_skip_black_lines(self):

        '''
        空 item 用 ‘’, na_values=['']  没跳过，不起作用

        默认 na 的值见 https://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_csv.html
        '''
        matrix = [
            [111, 'aaa', 'NULL'],  # NULL is Nan
            [222, 'NULL', 'mmm'],
            [''],
            [333, 'ccc', 'xxx'],
        ]

        local_data = matrix_2_bytes(matrix)

        self.assertEqual(len(matrix)
                         , len(pd.read_csv(BytesIO(local_data),
                                           names=g_column_names,
                                           header=None,
                                           sep='\t',
                                           skip_blank_lines=False)))

        self.assertEqual(len(matrix) - 1
                         , len(pd.read_csv(BytesIO(local_data),
                                           names=g_column_names,
                                           header=None,
                                           sep='\t',
                                           skip_blank_lines=True)
                               ))

    def test_drop_columns(self):

        chunk = self._basic_read()

        # give drop columns index's list
        v = chunk.columns[[1]]  # type= pandas.indexes.base.Index
        # axis : int or axis name
        chunk2 = chunk.drop(v, axis=1)

        names2 = g_column_names[:]
        names2.pop(1)

        self._dataframe_equal_matrix(
            chunk2,
            [
                [111, 'nnn'],
                [111, 'mmm'],
                [222, 'xxx'],
                [333, 'yyy'],
            ], names2
        )

        v = chunk.columns[[1, 2]]

        chunk3 = chunk.drop(v, axis=1)
        names3 = g_column_names[:]
        names3.pop(2)
        names3.pop(1)

        self._dataframe_equal_matrix(
            chunk3,
            [
                [111],
                [111],
                [222],
                [333],
            ], names3
        )

    def test_concat_with_same_columns(self):

        chunk1 = self._basic_read()

        chunk2 = pd.concat([chunk1, chunk1])

        matrix = g_data_matrix[:]

        matrix.extend(matrix)

        self._dataframe_equal_matrix(
            chunk2,
            matrix,
            g_column_names
        )

    def test_concat_with_different_columns_same_column_names(self):

        chunk1 = self._basic_read()

        self._dataframe_equal_matrix(
            chunk1, g_data_matrix, g_column_names
        )

        use_cols = g_column_names[:]
        use_cols.pop(1)
        chunk2 = pd.read_csv(BytesIO(g_data),
                             names=g_column_names,
                             header=None,
                             sep='\t',
                             usecols=use_cols)

        self._dataframe_equal_matrix(
            chunk2,
            [
                [111, 'nnn'],
                [111, 'mmm'],
                [222, 'xxx'],
                [333, 'yyy'],
            ]
            , use_cols
        )

        chunk3 = pd.concat([chunk1, chunk2])

        matrix = g_data_matrix[:]
        matrix.extend(
            [
                [111, '', 'nnn'],
                [111, '', 'mmm'],
                [222, '', 'xxx'],
                [333, '', 'yyy'],
            ]
        )

        chunk3 = chunk3.fillna('')

        self._dataframe_equal_matrix(
            chunk3, matrix, g_column_names  # The longest one
        )

    def test_concat_with_different_columns_different_column_names(self):

        chunk1 = self._basic_read()

        self._dataframe_equal_matrix(
            chunk1, g_data_matrix, g_column_names
        )

        matrix2 = [
            [666, 'zzz'],
            [888, 'hhh'],
            [999, 'ggg'],
        ]
        names2 = ['column_00', 'column_11']
        chunk2 = pd.read_csv(BytesIO(matrix_2_bytes(matrix2)),
                             names=names2,
                             header=None,
                             sep='\t')

        self._dataframe_equal_matrix(
            chunk2, matrix2, names2
        )

        chunk3 = pd.concat([chunk1, chunk2])

        # column name 会被排序

        names3 = ['column_0', 'column_00', 'column_1', 'column_11', 'column_2']

        matrix3 = [
            [111, '', 'aaa', '', 'nnn'],
            [111, '', 'bbb', '', 'mmm'],
            [222, '', 'ccc', '', 'xxx'],
            [333, '', 'ddd', '', 'yyy'],
            ['', 666, '', 'zzz', ''],
            ['', 888, '', 'hhh', ''],
            ['', 999, '', 'ggg', ''],
        ]

        chunk3 = chunk3.fillna('')

        self._dataframe_equal_matrix(
            chunk3, matrix3, names3
        )

    def test_sort_by(self):

        matrix = [
            [111, 'ccc'],
            [444, 'aaa'],
            [333, 'bbb'],
        ]
        names = ['colum_0', 'column_1']

        chunk = pd.read_csv(BytesIO(matrix_2_bytes(matrix)),
                            names=names,
                            header=None,
                            sep='\t')

        self._dataframe_equal_matrix(
            chunk.sort_values(by=[names[0]])
            , [
                [111, 'ccc'],
                [333, 'bbb'],
                [444, 'aaa'],
            ]
            , names
        )

        self._dataframe_equal_matrix(
            chunk.sort_values(by=[names[1]])
            , [
                [444, 'aaa'],
                [333, 'bbb'],
                [111, 'ccc'],
            ]
            , names
        )

    def test_save_to_file(self):

        chunk = self._basic_read()

        fullpath = os.path.join(curpath, 'test.bin')
        if os.path.exists(fullpath):
            os.remove(fullpath)

        chunk.to_csv(fullpath, sep='\t'
                     , index=False  # must
                     , header=False  # must
                     )

        chunk_check = pd.read_csv(fullpath,
                                  names=g_column_names,
                                  header=None,
                                  sep='\t')

        self._dataframe_equal_matrix(chunk, g_data_matrix, g_column_names)
        self._dataframe_equal_matrix(chunk_check, g_data_matrix, g_column_names)

        # rb read mode contains \r\n
        # r read mode contains \n
        with open(fullpath, 'r') as fr:
            c = fr.read()
            c = c.rstrip()
            self.assertEqual(g_data, c)

        os.remove(fullpath)

    def test_special_handle_columns_when_create(self):
        def _func_convert(text):
            try:
                return text + '_convert'
            except AttributeError:
                return text

        matrix = [
            ['nnn', 'aaa'],
            ['mmm', 'bbb'],
            ['yyy', 'ccc'],
        ]

        names = g_column_names[:]
        names.pop()

        chunk = pd.read_csv(BytesIO(matrix_2_bytes(matrix)),
                            names=names,
                            header=None,
                            sep='\t')

        self._dataframe_equal_matrix(chunk, matrix, names)

        chunk2 = pd.read_csv(BytesIO(matrix_2_bytes(matrix))
                             , names=names
                             , header=None
                             , sep='\t'
                             , converters={g_column_names[0]: _func_convert},  # 指定这一列使用什么函数转换
                             )

        self._dataframe_equal_matrix(chunk2, [
            ['nnn_convert', 'aaa'],
            ['mmm_convert', 'bbb'],
            ['yyy_convert', 'ccc'],
        ], names)

    def test_to_dict_list(self):

        chunk = self._basic_read()

        for k in chunk.iterrows():
            pass  # (row_index, row_Series)

        for k in chunk.iteritems():
            pass  # (column_name, column_Series)

        # type= pandas.indexes.base.Index
        for k in chunk.keys():
            pass  # column name

        for k in chunk.itertuples():
            pass  # type= pandas.core.frame.Pandas,
            # print (getattr(k,g_column_names[0]))   one row , with the column name attr, so result is [111, 111, 222, 333]

        self.assertEqual(chunk.keys().tolist(), chunk.columns.values.tolist())

        names = chunk.keys().tolist()

        r = [{k1: v1 for k1, v1 in zip(names, k[1].tolist())} for k in chunk.iterrows()]

        r_check = [{k1: v1 for k1, v1 in zip(g_column_names, row)} for row in g_data_matrix]

        self.assertEqual(r, r_check)

    def test_listed_a_column(self):

        chunk = self._basic_read()

        for col_idx in range(len(g_data_matrix[0])):
            self.assertEqual(
                [row[col_idx] for row in g_data_matrix]
                , chunk[g_column_names[col_idx]].tolist()
            )

    def test_get_column_names(self):

        chunk = self._basic_read()

        # recommended
        way1 = chunk.keys().tolist()
        way2 = chunk.columns.values.tolist()
        self.assertEqual(way1, way2)

    def test_column_name_to_column_index(self):
        chunk = self._basic_read()

        # type = int
        idx = chunk.columns.get_loc(g_column_names[1])

        for idx, name in enumerate(g_column_names):
            self.assertEqual(idx, chunk.columns.get_loc(name))

    def test_update_specific_item_value(self):

        chunk = self._basic_read()

        for idx, row in chunk.iterrows():
            if row[g_column_names[1]] == 'bbb':
                chunk.set_value(idx, g_column_names[1], 'eee')

        self._dataframe_equal_matrix(
            chunk
            , [
                [111, 'aaa', 'nnn'],
                [111, 'eee', 'mmm'],
                [222, 'ccc', 'xxx'],
                [333, 'ddd', 'yyy'],
            ]
            , g_column_names
        )

    def test_insert_new_column(self):

        chunk = self._basic_read()

        column_names = chunk.keys().tolist()
        last_column_idx = chunk.columns.get_loc(column_names[-1])

        # loc : int
        #    Must have 0 <= loc <= len(columns)
        chunk.insert(last_column_idx + 1, 'column_new_insert', 'default_value')

        self._dataframe_equal_matrix(chunk
                                     , [
                                         [111, 'aaa', 'nnn', 'default_value'],
                                         [111, 'bbb', 'mmm', 'default_value'],
                                         [222, 'ccc', 'xxx', 'default_value'],
                                         [333, 'ddd', 'yyy', 'default_value'],
                                     ]
                                     , column_names + ['column_new_insert']
                                     )

    def test_insert_new_column_2(self):
        chunk = self._basic_read()

        column_names = chunk.keys().tolist()

        # loc : int
        #    Must have 0 <= loc <= len(columns)
        chunk.insert(0, 'column_new_insert', 'default_value')
        column_names.insert(0, 'column_new_insert')

        self._dataframe_equal_matrix(chunk
                                     , [
                                         ['default_value', 111, 'aaa', 'nnn'],
                                         ['default_value', 111, 'bbb', 'mmm'],
                                         ['default_value', 222, 'ccc', 'xxx'],
                                         ['default_value', 333, 'ddd', 'yyy'],
                                     ]
                                     , column_names
                                     )

    def test_insert_new_columns(self):
        chunk = self._basic_read()

        column_names = chunk.keys().tolist()

        cs = ['column_new_insert_1', 'column_new_insert_2']

        # error, must once one column
        # chunk.insert(0, cs, 'default_value')

    def test_get_a_column_drop_duplcaties(self):

        chunk = self._basic_read()

        a = chunk[chunk.keys().tolist()[0]].drop_duplicates().tolist()
        a = set(a)

        a_check = set([ row[0] for row in g_data_matrix ])

        self.assertEqual(a, a_check)



if __name__ == '__main__':
    unittest.main()
