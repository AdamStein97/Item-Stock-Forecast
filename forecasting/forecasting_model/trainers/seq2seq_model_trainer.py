import tensorflow as tf
import time
from forecasting.forecasting_model.tf_models.seq2seq_forecast_model import Seq2SeqForecastModel
import forecasting as f
import os

class Seq2SeqTrainer():
    def __init__(self, loss_func=tf.keras.losses.mse, optimizer=tf.keras.optimizers.Adam, lr=1e-3, model_name='seq2seq_forecasting',
                 **kwargs):
        self.model = Seq2SeqForecastModel(**kwargs)
        self.loss_func = loss_func
        self.optimizer = optimizer(lr)

        self.train_loss = tf.keras.metrics.Mean(name='train_loss')

        self.val_loss = tf.keras.metrics.Mean(name='val_loss')

        self.val_loss_no_correction = tf.keras.metrics.Mean(name='val_loss_no_correction')
        self.model_name = model_name

    @tf.function
    def train_step(self, x, y):
        with tf.GradientTape() as tape:
            pred = self.model(x, correction_signal=y)
            loss = tf.reduce_mean(self.loss_func(pred, y))

        gradients = tape.gradient(loss, self.model.trainable_variables)

        self.optimizer.apply_gradients(zip(gradients, self.model.trainable_variables))
        self.train_loss(loss)

    @tf.function
    def eval_step(self, x, y):
        pred = self.model(x, correction_signal=y)
        loss = self.loss_func(pred, y)
        loss = tf.reduce_mean(loss)
        self.val_loss(loss)

        pred = self.model(x)
        loss = self.loss_func(pred, y)
        loss = tf.reduce_mean(loss)
        self.val_loss_no_correction(loss)

    def train_loop(self, train_dataset, test_dataset, epochs=90, **kwargs):
        ckpt = tf.train.Checkpoint(transformer=self.model,
                                   optimizer=self.optimizer)

        ckpt_manager = tf.train.CheckpointManager(ckpt, os.path.join(f.MODEL_DIR, self.model_name), max_to_keep=5)
        for epoch in range(epochs):
            start = time.time()
            for batch, (x, y) in enumerate(train_dataset):
                self.train_step(x, y)

                if batch % 25 == 0:
                    print('Batch {} Loss {:.4f}'.format(
                        batch, self.train_loss.result()))

            print('Epoch {} Loss {:.4f}'.format(
                epoch + 1, self.train_loss.result()))

            for (batch, (x, y)) in enumerate(test_dataset.take(20)):
                self.eval_step(x, y)

            print('Epoch {} Val Loss {:.4f} Val Loss No Correction {:.4f} '.format(
                epoch + 1, self.val_loss.result(), self.val_loss_no_correction.result()))

            self.train_loss.reset_states()
            self.val_loss.reset_states()
            self.val_loss_no_correction.reset_states()
            print('Time taken for 1 epoch {} sec\n'.format(time.time() - start))

            if (epoch + 1) % 3 == 0:
                ckpt_save_path = ckpt_manager.save()
                print('Saving checkpoint for epoch {} at {}'.format(epoch + 1,
                                                                    ckpt_save_path))
        return self.model

    def predict(self, trained_model, model_input):
        return trained_model(model_input)


