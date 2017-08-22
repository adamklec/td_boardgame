import tensorflow as tf
from envs.chess import ChessEnv


class ChessValueModel:
    def __init__(self):
        fv_size = ChessEnv.get_feature_vector_size()
        simple_value_weights = ChessEnv.get_simple_value_weights()
        with tf.variable_scope('neural_network'):
            with tf.variable_scope('simple_value_weights'):
                simple_value_weights = tf.get_variable('simple_value_weights',
                                                       initializer=tf.constant(simple_value_weights, dtype=tf.float32),
                                                       trainable=False)

            self.feature_vector_ = tf.placeholder(tf.float32, shape=[None, fv_size], name='feature_vector_')
            with tf.variable_scope('layer_1'):
                W_1 = tf.get_variable('W_1', initializer=tf.truncated_normal([fv_size, 500], stddev=0.01))
                self.simple_learned = tf.matmul(self.feature_vector_, W_1)
                hidden = tf.nn.relu(tf.matmul(self.feature_vector_, W_1), name='hidden')

            with tf.variable_scope('layer_2'):
                W_2 = tf.get_variable('W_2', initializer=tf.truncated_normal([500, 1], stddev=0.01))
                self.hidden = tf.matmul(hidden, W_2)

            simple_hidden = tf.matmul(1-self.feature_vector_, simple_value_weights)

            self.value = tf.tanh((simple_hidden + self.hidden) / 5.0)
            self.trainable_variables = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES,
                                                         scope=tf.get_variable_scope().name)

    def value_function(self, sess):
        def f(fv):
            value = sess.run(self.value,
                             feed_dict={self.feature_vector_: fv})
            return value

        return f

