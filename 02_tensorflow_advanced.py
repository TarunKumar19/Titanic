import os

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split

################################
# Preparing Data
################################

# read data from file
data = pd.read_csv('data/train.csv')

# fill nan values with 0
data = data.fillna(0)
# convert ['male', 'female'] values of Sex to [1, 0]
data['Sex'] = data['Sex'].apply(lambda s: 1 if s == 'male' else 0)
# 'Survived' is the label of one class,
# add 'Deceased' as the other class
data['Deceased'] = data['Survived'].apply(lambda s: 1 - s)

# select features and labels for training
dataset_X = data[['Sex', 'Age', 'Pclass', 'SibSp', 'Parch', 'Fare']]
dataset_X = dataset_X.as_matrix()
dataset_Y = data[['Survived', 'Deceased']]
dataset_Y = dataset_Y.as_matrix()

# split training data and validation set data
X_train, X_val, y_train, y_val = train_test_split(dataset_X, dataset_Y,
                                                  test_size=0.2,
                                                  random_state=42)

################################
# Constructing Dataflow Graph
################################

# arguments that can be set in command line
tf.app.flags.DEFINE_integer('epochs', 10, 'Training epochs')
FLAGS = tf.app.flags.FLAGS

with tf.name_scope('input'):
    # create symbolic variables
    X = tf.placeholder(tf.float32, shape=[None, 6])
    y_true = tf.placeholder(tf.float32, shape=[None, 2])

with tf.name_scope('logistic_regression'):
    # weights and bias are the variables to be trained
    weights = tf.Variable(tf.random_normal([6, 2]))
    bias = tf.Variable(tf.zeros([2]))
    y_pred = tf.nn.softmax(tf.matmul(X, weights) + bias)

    # add histogram summaries for weights, view on tensorboard
    tf.histogram_summary('weights', weights)
    tf.histogram_summary('bias', bias)

# Minimise cost using cross entropy
# NOTE: add a epsilon(1e-10) when calculate log(y_pred),
# otherwise the result will be -inf
with tf.name_scope('cost'):
    cross_entropy = - tf.reduce_sum(y_true * tf.log(y_pred + 1e-10),
                                    reduction_indices=1)
    cost = tf.reduce_mean(cross_entropy)
    tf.scalar_summary('loss', cost)

# use gradient descent optimizer to minimize cost
train_op = tf.train.GradientDescentOptimizer(0.001).minimize(cost)

with tf.name_scope('accuracy'):
    correct_pred = tf.equal(tf.argmax(y_true, 1), tf.argmax(y_pred, 1))
    acc_op = tf.reduce_mean(tf.cast(correct_pred, tf.float32))
    # Add scalar summary for accuracy
    tf.scalar_summary('accuracy', acc_op)

global_step = tf.Variable(0, name='global_step', trainable=False)
# use saver to save and restore model
saver = tf.train.Saver()

# this variable won't be stored, since it is declared after tf.train.Saver()
non_storable_variable = tf.Variable(777)

ckpt_dir = './ckpt_dir'
if not os.path.exists(ckpt_dir):
    os.makedirs(ckpt_dir)

################################
# Training the model
################################

# use session to run the calculation
with tf.Session() as sess:
    # create a log writer. run 'tensorboard --logdir=./logs'
    writer = tf.train.SummaryWriter('./logs', sess.graph)
    merged = tf.merge_all_summaries()

    # variables have to be initialized at the first place
    tf.initialize_all_variables().run()

    # restore variables from checkpoint if exists
    ckpt = tf.train.get_checkpoint_state(ckpt_dir)
    if ckpt and ckpt.model_checkpoint_path:
        print('Restoring from checkpoint: %s' % ckpt.model_checkpoint_path)
        saver.restore(sess, ckpt.model_checkpoint_path)

    start = global_step.eval()
    # training loop
    for epoch in range(start, FLAGS.epochs):
        total_loss = 0.
        for i in range(len(X_train)):
            # prepare feed data and run
            feed_dict = {X: [X_train[i]], y_true: [y_train[i]]}
            _, loss = sess.run([train_op, cost], feed_dict=feed_dict)
            total_loss += loss
        # display loss per epoch
        print('Epoch: %04d, loss=%.9f' % (epoch + 1, total_loss))

        summary, accuracy = sess.run([merged, acc_op],
                                     feed_dict={X: X_val, y_true: y_val})
        writer.add_summary(summary, epoch)  # Write summary
        print('Accuracy on validation set: %.9f' % accuracy)

        # set and update(eval) global_step with epoch
        global_step.assign(epoch).eval()
        saver.save(sess, ckpt_dir + '/logistic.ckpt',
                   global_step=global_step)

    print('Training complete!')

################################
# Evaluating on the test set
################################

# restore variables and run prediction in another session
with tf.Session() as sess:
    # restore variables from checkpoint if exists
    ckpt = tf.train.get_checkpoint_state(ckpt_dir)
    if ckpt and ckpt.model_checkpoint_path:
        print('Restoring from checkpoint: %s' % ckpt.model_checkpoint_path)
        saver.restore(sess, ckpt.model_checkpoint_path)

    # predict on test set
    pred = sess.run(y_pred, feed_dict={X: X_val})
    pred_class = np.argmax(pred, 1)
    true_class = np.argmax(y_val, 1)
    accuracy = np.mean(np.equal(pred_class, true_class).astype(np.float32))
    print('Predict accuracy: %.9f' % accuracy)