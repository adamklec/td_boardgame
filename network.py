import tensorflow as tf
import chess
import numpy as np


class ChessNeuralNetwork(object):
    def __init__(self, trainer, scope, test_only=False):
        self.trainer = trainer
        self.test_only = test_only

        with tf.variable_scope(scope):
            self.feature_vector_placeholder = tf.placeholder(tf.float32, shape=[None, 1025], name='feature_vector_placeholder')

            with tf.variable_scope('layer_1'):
                W_1 = tf.get_variable('W_1', initializer=tf.truncated_normal([1025, 100], stddev=0.1))
                b_1 = tf.get_variable('b_1', shape=[100], initializer=tf.constant_initializer(0.0))
                activation_1 = tf.nn.relu(tf.matmul(self.feature_vector_placeholder, W_1) + b_1, name='activation_1')

            with tf.variable_scope('layer_2'):
                W_2 = tf.get_variable('W_2', initializer=tf.truncated_normal([100, 1], stddev=0.1))
                b_2 = tf.get_variable('b_2', shape=[1],  initializer=tf.constant_initializer(0.0))

            self.value = tf.nn.tanh(tf.matmul(activation_1, W_2) + b_2, name='value')

            self.target_value_placeholder = tf.placeholder(tf.float32, shape=[], name='reward_placeholder')

            delta = self.target_value_placeholder - self.value

            grads = tf.gradients(self.value, tf.trainable_variables())

            lamda = tf.constant(0.7, name='lamda')

            traces = []
            update_traces = []
            reset_traces = []

            grad_accums = []
            update_accums = []
            reset_accums = []

            with tf.variable_scope('update_traces'):
                for grad, var in zip(grads, tf.trainable_variables()):
                    if grad is None:
                        grad = tf.zeros_like(var)
                    with tf.variable_scope('trace'):
                        trace = tf.Variable(tf.zeros(grad.get_shape()), trainable=False, name='trace')
                        traces.append(trace)

                        update_trace_op = trace.assign((lamda * trace) + grad)
                        update_traces.append(update_trace_op)

                        reset_trace_op = trace.assign(tf.zeros_like(trace))
                        reset_traces.append(reset_trace_op)

                        grad_accum = tf.Variable(tf.zeros(grad.get_shape()), trainable=False, name='trace')
                        grad_accums.append(grad_accum)

                        update_accum_op = grad_accum.assign((-tf.reduce_sum(delta) * trace) + grad_accum)
                        update_accums.append(update_accum_op)

                        reset_accum_op = trace.assign(tf.zeros_like(trace))
                        reset_accums.append(reset_accum_op)

            self.update_traces_op = tf.group(*update_traces)
            with tf.control_dependencies([self.update_traces_op]):
                self.update_accums_op = tf.group(*update_accums)

            self.reset_traces_op = tf.group(*reset_traces)
            self.reset_accums_op = tf.group(*reset_accums)

            if not self.test_only:
                master_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, 'master')
                self.apply_grads = self.trainer.apply_gradients(zip(grad_accums, master_vars))

                for var, trace, grad_accum in zip(tf.trainable_variables(), traces, grad_accums):
                    tf.summary.histogram(var.name, var)
                    tf.summary.histogram(var.name, grad_accum)


    @staticmethod
    def make_feature_vector(board):
        piece_matrix = np.zeros((64, len(chess.PIECE_TYPES) + 1, len(chess.COLORS)))

        # piece positions
        for piece in chess.PIECE_TYPES:
            for color in chess.COLORS:
                piece_matrix[:, piece, int(color)] = pad_bitmask(board.pieces_mask(piece, color))

        # en passant target squares
        if board.ep_square:
            piece_matrix[board.ep_square, len(chess.PIECE_TYPES), int(board.turn)] = 1

        reshaped_piece_matrix = piece_matrix.reshape((64, (len(chess.PIECE_TYPES) + 1) * len(chess.COLORS)))
        feature_array = np.zeros((64, (len(chess.PIECE_TYPES) + 1) * len(chess.COLORS) + 2))
        feature_array[:, :-2] = reshaped_piece_matrix

        # empty squares
        empty_squares = (reshaped_piece_matrix.sum(axis=1) == 0)
        feature_array[empty_squares, :-2] = 1

        # castling rights
        feature_array[:, -1] = pad_bitmask(board.castling_rights)

        feature_vector = np.zeros((1, 1025))
        feature_vector[0, :-1] = np.reshape(feature_array, (1024,))
        feature_vector[0, -1] = board.turn

        return feature_vector

def pad_bitmask(mask):
    mask = [int(s) for s in list(bin(mask)[2:])]
    while len(mask) < 64:
        mask.insert(0, 0)
    return np.array(mask)
