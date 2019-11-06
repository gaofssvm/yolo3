# -*- coding: utf-8 -*-

import tensorflow as tf
import os
from tqdm import tqdm

from yolo.loss import loss_fn


def train_fn(model, train_generator, valid_generator=None, learning_rate=1e-4, num_epoches=500, save_dname=None, ckpt_path='./tf_ckpts'):
    
    save_fname = _setup(save_dname)
    optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)

    epoch = tf.Variable(-1)
    ckpt = tf.train.Checkpoint(epoch=epoch, optimizer=optimizer, model=model)
    manager = tf.train.CheckpointManager(ckpt, ckpt_path, max_to_keep=1)
    if manager.latest_checkpoint:
        print("Restored from {}".format(manager.latest_checkpoint))
        status = ckpt.restore(manager.latest_checkpoint)
        # status.assert_consumed()
    else:
        print("\n    Initializing from scratch.")


    history = []
    for i in range(epoch.numpy() + 1, num_epoches):
        # 1. update params
        train_loss = _loop_train(model, optimizer, train_generator, i, ckpt_path)
        
        # 2. monitor validation loss
        if valid_generator:
            valid_loss = _loop_validation(model, valid_generator)
            loss_value = valid_loss
        else:
            loss_value = train_loss
        print("{}-th loss = {}, train_loss = {}".format(i, loss_value, train_loss))

        # 3. update weights
        history.append(loss_value)
        if save_fname is not None and loss_value == min(history):
            print("    update weight {}".format(loss_value))
            model.save_weights("{}.h5".format(save_fname))
            
    model.save_weights("{}.h5".format('last_weights'))

    return history


def _loop_train(model, optimizer, generator, epoch, ckpt_path):
    # one epoch
    
    n_steps = generator.steps_per_epoch
    loss_value = 0
    for _ in tqdm(range(n_steps)):
        xs, yolo_1, yolo_2, yolo_3 = generator.next_batch()
        ys = [yolo_1, yolo_2, yolo_3]
        grads, loss = _grad_fn(model, xs, ys)
        loss_value += loss
        optimizer.apply_gradients(zip(grads, model.trainable_variables))
    loss_value /= generator.steps_per_epoch

    ckpt = tf.train.Checkpoint(epoch=tf.Variable(epoch), optimizer=optimizer, model=model)
    manager = tf.train.CheckpointManager(ckpt, ckpt_path, max_to_keep=1)
    manager.save(epoch)

    return loss_value


def _loop_validation(model, generator):
    # one epoch
    n_steps = generator.steps_per_epoch
    loss_value = 0
    for _ in range(n_steps):
        xs, yolo_1, yolo_2, yolo_3 = generator.next_batch()
        ys = [yolo_1, yolo_2, yolo_3]
        ys_ = model(xs)
        loss_value += loss_fn(ys, ys_)
    loss_value /= generator.steps_per_epoch
    return loss_value


def _setup(save_dname):
    if save_dname:
        if not os.path.exists(save_dname):
            os.makedirs(save_dname)
        save_fname = os.path.join(save_dname, "weights")
    else:
        save_fname = None
    return save_fname


def _grad_fn(model, images_tensor, list_y_trues):
    with tf.GradientTape() as tape:
        logits = model(images_tensor)
        loss = loss_fn(list_y_trues, logits)
        # print("loss = ", loss)
    return tape.gradient(loss, model.trainable_variables), loss


if __name__ == '__main__':
    pass
